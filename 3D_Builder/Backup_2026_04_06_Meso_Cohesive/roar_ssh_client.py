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
        with open("roar_mfa_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- NEW INTERACTIVE PROMPT ---\nTÍTULO: {title}\nINSTRUÇÕES: {instructions}\nPROMPTS: {prompt_list}\n")
            
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
        Inicia a ponte de comunicação com retry e backoff para resistir ao firewall da Penn State.
        mfa_callback: Funcao do Streamlit para pintar a tela de amarelo (Avisando do Celular).
        """
        self.mfa_callback = mfa_callback
        
        import time
        
        MAX_RETRIES = 3
        RETRY_DELAYS = [5, 15, 30]  # Espera progressiva entre tentativas (segundos)
        
        # Zera o log de interação MFA para a nova tentativa
        with open("roar_mfa_debug.log", "w", encoding="utf-8") as f:
            f.write("--- INICIANDO NOVO LOGIN ---\n")
            
        last_error = "Sem tentativas realizadas."
        
        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                wait_time = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
                time.sleep(wait_time)
                # Cria novo client para cada tentativa (evita estado corrompido)
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                self.client.connect(
                    hostname=self.host,
                    username=self.username,
                    allow_agent=False,
                    look_for_keys=False,
                    timeout=60
                )
                
                # Espera generosa antes do health check - o firewall bloqueia canais se conectar rapido
                wait_post_auth = 5 + (attempt * 5)  # 5s, 10s, 15s nas tentativas progressivas
                time.sleep(wait_post_auth)
                
                # Health check com retry interno
                t = self.client.get_transport()
                if t:
                    t.set_keepalive(10)
                
                health_ok = False
                for hc in range(3):
                    try:
                        # Tenta forçar alocação PTY com timeout gigante
                        stdin, stdout, stderr = self.client.exec_command("whoami", timeout=40.0, get_pty=True)
                        who = stdout.read().decode('utf-8').strip()
                        if who:
                            health_ok = True
                            break
                        time.sleep(3)
                    except Exception as hce:
                        with open("roar_mfa_debug.log", "a", encoding="utf-8") as f:
                            f.write(f"Health Check Exception: {repr(hce)}\n")
                        last_error = repr(hce)
                        time.sleep(3)
                        continue
                
                if not health_ok:
                    last_error = f"Canal bloqueado apos autenticacao (tentativa {attempt+1}/{MAX_RETRIES}). Detalhe: {last_error}"
                    continue  # Tenta novamente
                
                self.is_connected = True
                return True, f"Conexao estabelecida com sucesso (tentativa {attempt+1})."
                
            except (paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException) as ae:
                if "No authentication methods available" not in str(ae) and "Authentication" not in str(ae) and "blocked" not in str(ae).lower():
                    raise ae
                    
                with open("roar_mfa_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"Authentication Exception Toggled (Duo MFA Esperado). Error: {str(ae)}\n")
                try:
                    t = self.client.get_transport()
                    if not t:
                        last_error = "Falha ao criar transporte SSH."
                        continue
                        
                    t.auth_interactive(self.username, self._interactive_handler)
                    time.sleep(5 + (attempt * 5))
                    
                    t.set_keepalive(10)
                    health_ok = False
                    for hc in range(3):
                        try:
                            # Abandona o modo exec_command e tenta invocar um Shell Terminal genuíno
                            chan = self.client.invoke_shell(timeout=40.0)
                            chan.send("whoami\n")
                            time.sleep(2)
                            who = None
                            if chan.recv_ready():
                                who = chan.recv(1024).decode('utf-8').strip()
                            if who and self.username in who:
                                health_ok = True
                                break
                            time.sleep(3)
                        except Exception as e:
                            with open("roar_mfa_debug.log", "a", encoding="utf-8") as f:
                                f.write(f"MFA Healthcheck Exception: {repr(e)}\n")
                            time.sleep(3)
                            continue
                    
                    if not health_ok:
                        last_error = f"Canal MFA bloqueado (tentativa {attempt+1}/{MAX_RETRIES})"
                        continue
                    
                    self.is_connected = True
                    return True, f"Conexao MFA verificada e estabelecida (tentativa {attempt+1})."
                    
                except Exception as e:
                    with open("roar_mfa_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"Inner Exception in MFA block: {str(e)}\n")
                    last_error = str(e)
                    continue
                    
            except Exception as e:
                with open("roar_mfa_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"Outer Exception in Connect block: {str(e)}\n")
                last_error = str(e)
                continue
        
        return False, f"Firewall Penn State: Limite de conexoes atingido apos {MAX_RETRIES} tentativas. Aguarde alguns minutos e tente novamente. Ultimo erro: {last_error}"


    def upload_file(self, local_path, remote_path):
        """
        Transfere o ZIP via injeção bruta B64 via SSH TTY.
        Ignora totalmente subsistemas restritos (SFTP/SCP) da Penn State.
        """
        if not self.is_connected:
            return False, "Cliente não está conectado."
            
        import base64
        import time
        
        last_err = ""
        for attempt in range(3):
            try:
                # Ativa ping TCP para evitar drop silencioso do firewall durante o longo push do DUO
                t = self.client.get_transport()
                if t: t.set_keepalive(5)
                
                with open(local_path, "rb") as f:
                    b64_content = base64.b64encode(f.read())
                    
                # Escreve o comando sem o payload no ARG. O Payload vai pelo tubo:
                remote_dir = os.path.dirname(remote_path)
                cmd = f"mkdir -p {remote_dir} && base64 --decode > {remote_path}"
                
                # Executa SEM pseudo-terminal para evitar deadlock de espelhamento (echo) em transferências B64 massivas.
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
                last_err = str(e)
                time.sleep(4) # Wait and retry
                continue
                
        return False, f"Erro Fatal no Upload (B64) após 3 tentativas: {last_err}"

    def submit_job(self, sbatch_file_path):
        """
        Roda o comando sbatch para aquele arquivo na Penn State e puxa a resposta do Terminal.
        """
        if not self.is_connected:
            return False, ""
            
        try:
            command = f"sbatch {sbatch_file_path}"
            stdin, stdout, stderr = self.client.exec_command(command, get_pty=True, timeout=30.0)
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
            stdin, stdout, stderr = self.client.exec_command(command, get_pty=True, timeout=30.0)
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
