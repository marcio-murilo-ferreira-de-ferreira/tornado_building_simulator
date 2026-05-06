import paramiko
import time
import getpass
import os

class RoarSSHClient:
    """
    Cliente SSH e SFTP oficial e legítimo para conectar ao Roar Collab (Penn State).
    Suporta autenticação 'Keyboard-Interactive' necessária para interceptar e aguardar 
    o Duo Push (MFA) sem quebrar scripts automatizados.
    """
    
    def __init__(self, username, password, host="submit.hpc.psu.edu"):
        self.username = username
        self.password = password
        self.host = host
        
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.is_connected = False
        
    def _interactive_handler(self, title, instructions, prompt_list):
        """
        Handler interno que o Paramiko chama ao bater de frente com um desafio do servidor.
        Na PSU, o servidor geralmente pede a senha ou pergunta qual método Duo usar.
        """
        import json
        with open("roar_mfa_debug.log", "w", encoding="utf-8") as f:
            f.write(f"TÍTULO: {title}\nINSTRUÇÕES: {instructions}\nPROMPTS: {prompt_list}\n")
            
        responses = []
        for prompt_text, is_password in prompt_list:
            p_lower = prompt_text.strip().lower()
            
            # ATENÇÃO REDOBRADA: Muitas vezes a Penn State pede a senha DUAS vezes. 
            # Uma nativamente e outra como primeira pergunta do Pluggable Authentication!
            if 'password' in p_lower or 'senha' in p_lower:
                responses.append(self.password)
                
            # Se for EXPLICITAMENTE o prompt de MFA (Duo / Passcode)
            elif 'passcode' in p_lower or 'duo' in p_lower or 'option' in p_lower:
                if self.mfa_callback:
                    self.mfa_callback()
                
                # '1' é geralmente a opção de Push do Duo para a PSU
                responses.append('1')
            else:
                # Se não sabemos o que é, mandamos a senha de novo por garantia
                responses.append(self.password)
                
        return responses

    def connect(self, mfa_callback=None):
        """
        Inicia a ponte de comunicação.
        mfa_callback: Função do Streamlit para pintar a tela de amarelo (Avisando do Celular).
        """
        self.mfa_callback = mfa_callback
        
        try:
            # Tenta conectar via senha padrão primeiro. Às vezes o Duo é disparado nativamente pelo PAM (Pluggable Auth).
            self.client.connect(
                hostname=self.host,
                username=self.username,
                password=self.password,
                allow_agent=False,
                look_for_keys=False,
                timeout=30 # Aguarda um pouco a resposta do servidor
            )
            self.is_connected = True
            return True, "Conexão estabelecida com sucesso."
            
        except paramiko.ssh_exception.AuthenticationException:
            # O Login negou porque exige `Keyboard-Interactive` (O prompt do DUO)!
            try:
                t = self.client.get_transport()
                if not t:
                    return False, "Falha ao criar transporte SSH."
                    
                t.auth_interactive(self.username, self._interactive_handler)
                
                self.is_connected = True
                return True, "Conexão MFA verificada e estabelecida com sucesso."
                
            except Exception as e:
                try:
                    with open("roar_mfa_debug.log", "r", encoding="utf-8") as f:
                        server_questions = f.read()
                except:
                    server_questions = "Log não gerado."
                return False, f"Desafio DUO Interativo falhou: {str(e)} -> O ROAR ENVIOU A SEGUINTE PERGUNTA QUE ENGASGAMOS:\n{server_questions}"
                
        except Exception as e:
            return False, f"Erro Crítico de Conexão: {str(e)}"

    def upload_file(self, local_path, remote_path):
        """
        Transfere o ZIP via injeção bruta B64 via SSH TTY.
        Ignora totalmente subsistemas restritos (SFTP/SCP) da Penn State.
        """
        if not self.is_connected:
            return False, "Cliente não está conectado."
            
        import base64
        
        try:
            with open(local_path, "rb") as f:
                b64_content = base64.b64encode(f.read())
                
            # Escreve o comando sem o payload no ARG. O Payload vai pelo tubo:
            remote_dir = os.path.dirname(remote_path)
            cmd = f"mkdir -p {remote_dir} && base64 --decode > {remote_path}"
            
            # Executa com PTY garantindo a pipe
            stdin, stdout, stderr = self.client.exec_command(cmd, timeout=60.0)
            
            # Despeja a string base64 GIGANTE pelo tubo binário do STDIN silenciosamente
            stdin.write(b64_content)
            stdin.channel.shutdown_write() # Avisa ao linux remoto que o texto acabou
            stdin.close()
            
            stdout.channel.settimeout(30.0)
            err = stderr.read().decode('utf-8').strip() if stderr else ""
            
            if err:
                 return False, f"Falha na injeção B64 por STDIN: {err}"
            return True, f"Arquivo {os.path.basename(local_path)} injetado na Penn State com Tática Invisível."
        except Exception as e:
            return False, f"Erro Fatal no Upload (B64): {str(e)}"

    def submit_job(self, sbatch_file_path):
        """
        Roda o comando sbatch para aquele arquivo na Penn State e puxa a resposta do Terminal.
        """
        if not self.is_connected:
            return False, ""
            
        try:
            command = f"sbatch {sbatch_file_path}"
            stdin, stdout, stderr = self.client.exec_command(command, get_pty=True, timeout=60.0)
            stdout.channel.settimeout(30.0)
            
            out = stdout.read().decode('utf-8').strip()
            err = stderr.read().decode('utf-8').strip() if stderr else ""
            
            if err:
                return False, err
            return True, out
        except Exception as e:
            return False, f"Timeout no Submeter SLURM: {str(e)}"
        
    def exec_command(self, command):
        """
        Roda um comando arbitrário no terminal SSH protegido e retorna a saída.
        """
        if not self.is_connected:
            return False, "Not connected"
            
        try:
            stdin, stdout, stderr = self.client.exec_command(command, get_pty=True, timeout=60.0)
            stdout.channel.settimeout(30.0)
            
            out = stdout.read().decode('utf-8').strip()
            err = stderr.read().decode('utf-8').strip() if stderr else ""
            
            if err and "mkdir" not in command and "unzip" not in command:
                return False, err
            return True, out
        except Exception as e:
            return False, f"Timeout na Execução do Roar: {str(e)}"
    def check_job_status(self, job_id):
        """
        Verifica o status do Job no SLURM queue. Retorna (Success, Is_Running, Message).
        Se o job_id não estiver mais no squeue, assume-se concluído.
        """
        if not self.is_connected:
            return False, False, "Not connected"
            
        try:
            # -h tira cabecalho, -o %T retorna so o Estado (RUNNING, PENDING, COMPLETED)
            success, out = self.exec_command(f"squeue -j {job_id} -h -o '%T'")
            status = out.strip()
            
            if not status:
                # Se não tem saída no squeue, o job terminou (pode ser success ou fail)
                return True, False, "COMPLETED"
                
            return True, True, status
        except Exception as e:
            return False, False, f"Failed checking status: {str(e)}"

    def download_results_b64(self, remote_dir, local_zip_path):
        """
        Gera um ZIP contendo os resultados (.odb, relatórios) no servidor Roar.
        Baixa via STDOUT Base64 stream para evadir bloqueios de porta SCP.
        """
        if not self.is_connected:
            return False, "Not connected"
            
        import base64
        
        try:
            # Zipa todos os resultados gerados, cria stream para stdout, converte B64 em linha contínua
            cmd = f"cd {remote_dir} && zip -r -q - . | base64 -w 0"
            
            # Tempo elevado (600s) pois arquivos ODB podem ser grandes
            stdin, stdout, stderr = self.client.exec_command(cmd, get_pty=False, timeout=600.0)
            stdout.channel.settimeout(600.0)
            
            b64_str = stdout.read().decode('utf-8').strip()
            err = stderr.read().decode('utf-8').strip() if stderr else ""
            
            if err and "warning" not in err.lower():
                return False, f"Falha no empacotamento remoto: {err}"
                
            if not b64_str:
                 return False, "Nenhum dado de resultado recebido do túnel Roar."
                 
            with open(local_zip_path, "wb") as f:
                f.write(base64.b64decode(b64_str))
                
            return True, f"Resultados capturados da rede via B64 e salvos com sucesso."
        except Exception as e:
            return False, f"Erro Fatal no Download Reverso (B64): {str(e)}"

    def close(self):
        if self.is_connected and self.client:
            self.client.close()
            self.is_connected = False
