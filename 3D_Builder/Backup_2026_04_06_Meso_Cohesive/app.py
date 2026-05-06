import streamlit as st
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import plotly.graph_objects as go
import numpy as np
from abaqus_generator import generate_abaqus_script
from chrono_generator import generate_chrono_script

def generate_wall_preview(model_type, wall_width, wall_height, wall_thickness, 
                          building_depth=3.0, slab_thickness=0.15,
                          window_offset_x=None, sill_height=None, window_width=None, window_height=None,
                          brick_length=0.203, brick_height=0.057, brick_depth=0.095, mortar_thickness=0.010, wythes=1):
    
    fig = go.Figure()
    
    # Calculate window bounds if existing
    if window_width and window_height:
        w_xMin = window_offset_x
        w_xMax = window_offset_x + window_width
        w_yMin = sill_height
        w_yMax = sill_height + window_height
    else:
        w_xMin, w_xMax, w_yMin, w_yMax = -1, -1, -1, -1 # No window

    if "Macro-model" in model_type:
        blocks = []
        # South Wall
        if window_width and window_height:
            blocks.extend([
                dict(x=[0, wall_width], y=[0, w_yMin], z=[building_depth - wall_thickness, building_depth]), # Bottom
                dict(x=[0, wall_width], y=[w_yMax, wall_height], z=[building_depth - wall_thickness, building_depth]), # Top
                dict(x=[0, w_xMin], y=[w_yMin, w_yMax], z=[building_depth - wall_thickness, building_depth]), # Left
                dict(x=[w_xMax, wall_width], y=[w_yMin, w_yMax], z=[building_depth - wall_thickness, building_depth]) # Right
            ])
        else:
            blocks.append(dict(x=[0, wall_width], y=[0, wall_height], z=[building_depth - wall_thickness, building_depth]))
            
        # North Wall
        blocks.append(dict(x=[0, wall_width], y=[0, wall_height], z=[0, wall_thickness]))
        # West Wall
        blocks.append(dict(x=[0, wall_thickness], y=[0, wall_height], z=[wall_thickness, building_depth - wall_thickness]))
        # East Wall
        blocks.append(dict(x=[wall_width - wall_thickness, wall_width], y=[0, wall_height], z=[wall_thickness, building_depth - wall_thickness]))
        
        # Floor & Roof Slabs
        blocks.append(dict(x=[0, wall_width], y=[-slab_thickness, 0], z=[0, building_depth]))
        blocks.append(dict(x=[0, wall_width], y=[wall_height, wall_height + slab_thickness], z=[0, building_depth]))
        
        color = 'rgba(169, 169, 169, 0.95)' # DarkGray
    else:
        blocks = []
        num_bricks_x = int(wall_width / (brick_length + mortar_thickness)) + 2
        num_bricks_y = int(wall_height / (brick_height + mortar_thickness)) + 1
        
        max_draw = 2000 # Browser stability limit
        count = 0
        
        for w in range(wythes):
            z_start = building_depth - wall_thickness + w * (brick_depth + mortar_thickness)
            z_end = z_start + brick_depth
            for j in range(num_bricks_y):
                y_start = j * (brick_height + mortar_thickness)
                y_end = y_start + brick_height
                if y_start > wall_height: break
                
                offset = (brick_length / 2.0) if (j % 2 != 0) else 0.0
                for i in range(num_bricks_x):
                    x_start = i * (brick_length + mortar_thickness) - offset
                    x_end = x_start + brick_length
                    
                    if x_end < 0: continue
                    if x_start < 0: x_start = 0
                    if x_end > wall_width: x_end = wall_width
                    if y_end > wall_height: y_end = wall_height
                    
                    # Window Boolean Slicing
                    if w_yMin < y_end and y_start < w_yMax:
                        if x_start >= w_xMin and x_end <= w_xMax:
                            continue # Entirely engulfed
                        elif x_start < w_xMin and x_end > w_xMax:
                            # Cleave brick into two nodes (spans the entire small window)
                            if w_xMin - x_start >= 0.01:
                                blocks.append(dict(x=[x_start, w_xMin], y=[y_start, y_end], z=[z_start, z_end]))
                                count += 1
                            x_start = w_xMax
                        elif x_start < w_xMin and x_end > w_xMin:
                            x_end = w_xMin # Slice Right
                        elif x_start < w_xMax and x_end > w_xMax:
                            x_start = w_xMax # Slice Left
                            
                    if x_end - x_start < 0.01: continue
                        
                    blocks.append(dict(x=[x_start, x_end], y=[y_start, y_end], z=[z_start, z_end]))
                    count += 1
                    if count >= max_draw: break
                if count >= max_draw: break
            if count >= max_draw: break
        
        # Add proxy solid blocks for the rest of the Box to not blow up browser memory
        blocks.append(dict(x=[0, wall_width], y=[0, wall_height], z=[0, wall_thickness])) # North
        blocks.append(dict(x=[0, wall_thickness], y=[0, wall_height], z=[wall_thickness, building_depth - wall_thickness])) # West
        blocks.append(dict(x=[wall_width - wall_thickness, wall_width], y=[0, wall_height], z=[wall_thickness, building_depth - wall_thickness])) # East
        blocks.append(dict(x=[0, wall_width], y=[-slab_thickness, 0], z=[0, building_depth])) # Floor Slab
        blocks.append(dict(x=[0, wall_width], y=[wall_height, wall_height + slab_thickness], z=[0, building_depth])) # Roof Slab

        color = 'rgba(178, 34, 34, 1.0)' # Firebrick

    verts, i, j, k = [], [], [], []
    v_idx = 0
    for b in blocks:
        xs, xe, ys, ye, zs, ze = b['x'][0], b['x'][1], b['y'][0], b['y'][1], b['z'][0], b['z'][1]
        box_verts = [
            [xs, ys, zs], [xe, ys, zs], [xe, ye, zs], [xs, ye, zs],
            [xs, ys, ze], [xe, ys, ze], [xe, ye, ze], [xs, ye, ze]
        ]
        verts.extend(box_verts)
        box_faces = [
            [0,1,2], [0,2,3], [4,5,6], [4,6,7], [0,1,5], [0,5,4],
            [2,3,7], [2,7,6], [1,2,6], [1,6,5], [0,3,7], [0,7,4]
        ]
        for f in box_faces:
            i.append(f[0] + v_idx); j.append(f[1] + v_idx); k.append(f[2] + v_idx)
        v_idx += 8

    verts = np.array(verts) if len(verts) > 0 else np.zeros((0,3))
    if len(verts) > 0:
        fig.add_trace(go.Mesh3d(
            x=verts[:,0], y=verts[:,1], z=verts[:,2], i=i, j=j, k=k,
            color=color, flatshading=True,
            lighting=dict(ambient=0.6, diffuse=0.9, fresnel=0.1, specular=0.1, roughness=0.6)
        ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X (Width) [m]', range=[-1, wall_width+1], showbackground=False),
            yaxis=dict(title='Y (Height) [m]', range=[-1, wall_height+slab_thickness+1], showbackground=False),
            zaxis=dict(title='Z (Depth) [m]', range=[-1, building_depth+1], showbackground=False),
            aspectmode='data',
            camera=dict(eye=dict(x=-1.5, y=0.8, z=-1.5)) # Look predominantly from South-West (front/side)
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        height=500
    )
    return fig


# Set page config
st.set_page_config(
    page_title="Masonry Box Simulator (Explicit)",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    .stSlider > div > div > div > div {
        background-color: #3B82F6;
    }
    .section-title {
        font-size: 1.8rem;
        font-weight: 600;
        color: #1F2937;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #E5E7EB;
        padding-bottom: 0.5rem;
    }
    
    /* Increase base text and markdown sizes */
    .stMarkdown, p, div[data-testid="stMarkdownContainer"] {
        font-size: 1.2rem !important;
    }
    
    /* Increase Slider Labels and Input Labels */
    .stSlider label, .stRadio label, .stToggle label, .stTextInput label, div[data-testid="stWidgetLabel"] p {
        font-size: 1.3rem !important;
        font-weight: 500 !important;
    }
    
    /* Increase Slider numbering and values and Fix Spacing */
    div[data-testid="stThumbValue"], div[data-testid="stTickBarMax"], div[data-testid="stTickBarMin"], div.st-af {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }
    
    /* Add extra margin below slider numbers to push them up off the bar */
    div[data-testid="stThumbValue"] {
        margin-bottom: 8px !important;
        transform: translateY(-8px) !important; /* Pull it further up */
    }
    
    /* Thicken the Slider Track (Rail and Fill) */
    .stSlider > div > div > div > div {
        height: 6px !important;  /* Active filled blue portion */
    }
    div[data-baseweb="slider"] > div > div:first-child {
        height: 6px !important;  /* Gray background rail */
        border-radius: 4px;
    }
    
    /* Increase Button text */
    button p {
        font-size: 1.2rem !important;
    }
    
    /* Scale radio options */
    div[role="radiogroup"] label {
        font-size: 1.1rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Application Header
st.markdown('<div class="main-header">Abaqus/Chrono Masonry Box Simulator (Explicit)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Parametric generation of 3D Building Dynamic Collapse using Explicit CDP and Rigid-Body Multi-physics</div>', unsafe_allow_html=True)

# Sidebar for Execution Environment
with st.sidebar:
    st.markdown('<div class="section-title" style="margin-top:0;">Execution Environment</div>', unsafe_allow_html=True)
    run_env = st.radio("Select Target Environment:", ["💻 Local Computer", "🦁 Penn State Roar (SLURM)"])
    
    st.markdown("---")
    if "Penn State Roar" in run_env:
        st.info("Log in with your PSU credentials to offload the Abaqus simulation to the Supercomputer.")
        psu_user = st.text_input("PSU Username (e.g. mxf53)", value="")
        psu_pass = st.text_input("Password", type="password")
        st.warning("📱 Keep your phone ready for the Duo MFA Push!")
        run_mode = "ROAR"
    else:
        st.success("Simulations will run on this local machine using the configured PATH.")
        run_mode = "LOCAL"

# Layout with two main columns
input_col, script_col, plot_col = st.columns([1.2, 1.2, 1.5])

with input_col:
    st.markdown('<div class="section-title">Model Approach</div>', unsafe_allow_html=True)
    model_type = st.radio("Select Modeling Strategy", ["1. Smooth Wall (Macro-model)", "2. Interlocking Brick Wall (Meso-model)"])


    st.markdown('<div class="section-title">Building Geometry</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        wall_height = st.slider("Building Height (m)", min_value=2.0, max_value=6.0, value=3.0, step=0.1)
    with col2:
        wall_width = st.slider("Building Length X (m)", min_value=2.0, max_value=10.0, value=3.0, step=0.1)
    with col3:
        building_depth = st.slider("Building Depth Z (m)", min_value=2.0, max_value=10.0, value=3.0, step=0.1)
    with col4:
        slab_thickness = st.slider("Concrete Slab Thick (m)", min_value=0.1, max_value=0.5, value=0.15, step=0.05)
        
    if "Macro-model" in model_type:
        wall_thickness = st.slider("Wall Thickness (m)", min_value=0.1, max_value=0.6, value=0.2, step=0.05)
        # Default empty brick params so they are always defined
        brick_length, brick_height, brick_depth, mortar_thickness, wythes = 0.2, 0.06, 0.1, 0.01, 1
    else:
        st.markdown("**Brick & Mortar Properties (Historic Pennsylvania Default)**")
        b_col1, b_col2, b_col3, b_col4 = st.columns(4)
        with b_col1:
            brick_length = st.number_input("Brick Length (m)", value=0.203, step=0.001, format="%.3f")
        with b_col2:
            brick_height = st.number_input("Brick Height (m)", value=0.057, step=0.001, format="%.3f")
        with b_col3:
            brick_depth = st.number_input("Brick Depth (m)", value=0.095, step=0.001, format="%.3f")
        with b_col4:
            mortar_thickness = st.number_input("Mortar Thick (m)", value=0.010, step=0.001, format="%.3f")
            
        wythes = st.slider("Number of Wythes (Camadas de espessura)", min_value=1, max_value=4, value=2, step=1)
        # Calculate wall thickness based on brick wythes and mortar joints between them
        wall_thickness = wythes * brick_depth + max(0, wythes - 1) * mortar_thickness
        st.info(f"Calculated 3D Wall Thickness: **{wall_thickness:.3f} m**")

    st.markdown('<div class="section-title">Support & Roof Conditions</div>', unsafe_allow_html=True)
    has_roof_slab = st.toggle("Simulate Top Support (Concrete Roof Slab / Tie)", value=True, help="If active, perfectly locks the top row of bricks against out-of-plane displacement, capturing typical confined masonry response. If OFF, models a freestanding unreinforced wall acting as a cantilever parapet from the floor.")

    st.markdown('<div class="section-title">Openings (Windows/Doors)</div>', unsafe_allow_html=True)
    has_window = st.toggle("Include Window Opening", value=True)
    
    if has_window:
        w_col1, w_col2, w_col3, w_col4 = st.columns(4)
        with w_col1:
            window_width = st.slider("Window Width (m)", min_value=0.5, max_value=wall_width-1.0, value=1.0, step=0.1)
        with w_col2:
            window_height = st.slider("Window Height (m)", min_value=0.5, max_value=wall_height-1.0, value=1.2, step=0.1)
        with w_col3:
            sill_height = st.slider("Sill Height (m)", min_value=0.0, max_value=wall_height-window_height-0.2, value=0.9, step=0.1)
        with w_col4:
            max_offset = max(0.0, wall_width - window_width)
            default_offset = max_offset / 2.0
            window_offset_x = st.slider("X Offset (m)", min_value=0.0, max_value=max_offset, value=default_offset, step=0.1)
    else:
        window_width = 0.0
        window_height = 0.0
        sill_height = 0.0
        window_offset_x = 0.0

    st.markdown('<div class="section-title">Lateral Wind Load</div>', unsafe_allow_html=True)
    st.info("Wind pressure is converted to nodal/face loads applied to the surface.")
    
    tornado_class = st.selectbox("Tornado Wind Class (ASCE/EF Scale)", 
                                 ["Manual Input", 
                                  "EF-0 (Weak, ~0.8 kPa)", 
                                  "EF-1 (Moderate, ~1.5 kPa)", 
                                  "EF-2 (Significant, ~2.5 kPa)", 
                                  "EF-3 (Severe, ~4.0 kPa)", 
                                  "EF-4 (Devastating, ~6.0 kPa)", 
                                  "EF-5 (Incredible, ~8.5 kPa)"])
                                  
    if tornado_class == "Manual Input":
        wind_pressure = st.slider("Wind Pressure (kPa)", min_value=0.0, max_value=50.0, value=1.5, step=0.1)
    else:
        # Extract the approximate numerical value from the string
        pressure_val = float(tornado_class.split('~')[1].split(' ')[0])
        wind_pressure = st.slider("Wind Pressure (kPa)", min_value=0.0, max_value=50.0, value=pressure_val, step=0.1, disabled=True)
        
    wind_duration = st.slider("Wind Gust Duration (seconds)", min_value=0.1, max_value=2.0, value=0.5, step=0.1)
    wind_direction = st.radio("Wind Direction", ["South Wall (Head-on)", "East Wall (Lateral)", "Internal Pressurization (Window Failure)"], horizontal=False)
    apply_decay_field = st.checkbox("Asymmetric Wind Decay (Analytical Field)", value=False, help="Applies a 3D Analytical Equation to make the pressure decay radially from the window center, simulating realistic fluid vortex impacts.")
    
    st.markdown('<div class="section-title">Structural Retrofit</div>', unsafe_allow_html=True)
    apply_frp = st.toggle("Apply FRP Retrofit (Carbon Fiber Strips)", value=False)
    if apply_frp:
        frp_spacing = st.slider("FRP Strip Spacing (m)", min_value=0.5, max_value=2.0, value=1.0, step=0.1)

with plot_col:
    st.markdown('<div class="section-title">2D Schematic Preview</div>', unsafe_allow_html=True)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 12), gridspec_kw={'height_ratios': [1, 1]})
    
    # --- Top-Down View (Planta Baixa) on ax1 ---
    # Draw South, North, East, West walls
    s_rect = patches.Rectangle((0, 0), wall_width, wall_thickness, linewidth=1.5, edgecolor='#1F2937', facecolor='#9CA3AF')
    n_rect = patches.Rectangle((0, building_depth - wall_thickness), wall_width, wall_thickness, linewidth=1.5, edgecolor='#1F2937', facecolor='#9CA3AF')
    e_rect = patches.Rectangle((wall_width - wall_thickness, wall_thickness), wall_thickness, building_depth - 2*wall_thickness, linewidth=1.5, edgecolor='#1F2937', facecolor='#9CA3AF')
    w_rect = patches.Rectangle((0, wall_thickness), wall_thickness, building_depth - 2*wall_thickness, linewidth=1.5, edgecolor='#1F2937', facecolor='#9CA3AF')
    
    ax1.add_patch(s_rect)
    ax1.add_patch(n_rect)
    ax1.add_patch(e_rect)
    ax1.add_patch(w_rect)
    
    # Indicate Wind Direction
    if wind_direction == "South Wall (Head-on)":
        ax1.annotate("WIND (South)", xy=(wall_width/2, 0.0), xytext=(wall_width/2, -1.0),
                     arrowprops=dict(facecolor='#2563EB', shrink=0.05, width=4, headwidth=12), 
                     fontsize=12, weight='bold', color='#2563EB', ha='center')
    elif wind_direction == "East Wall (Lateral)":
        ax1.annotate("WIND (East)", xy=(wall_width, building_depth/2), xytext=(wall_width + 1.5, building_depth/2),
                     arrowprops=dict(facecolor='#DC2626', shrink=0.05, width=4, headwidth=12), 
                     fontsize=12, weight='bold', color='#DC2626', ha='center', va='center')
    else:
        # Internal Pressurization
        ax1.annotate("INTERNAL PRESSURIZATION", xy=(wall_width/2, building_depth/2), xytext=(wall_width/2, building_depth/2),
                     fontsize=9, weight='bold', color='#B91C1C', ha='center', va='center')
    
    # Floor Slab Representation (dashed outline)
    slab_rect = patches.Rectangle((0, 0), wall_width, building_depth, linewidth=2, edgecolor='#10B981', facecolor='none', linestyle='--')
    ax1.add_patch(slab_rect)
    ax1.annotate(f"Floor/Roof Slab", xy=(wall_width/2, building_depth/2), color='#10B981', weight='bold', ha='center', va='center', alpha=0.8)
    
    ax1.set_xlim(-1.0, wall_width + 1.0)
    ax1.set_ylim(-1.5, building_depth + 1.0)
    ax1.set_aspect('equal')
    ax1.set_xlabel("Length X (m)")
    ax1.set_ylabel("Depth Z (m)")
    ax1.set_title(f"Top-Down Plan View ({wall_width:.1f}m x {building_depth:.1f}m)", fontweight='bold', fontsize=14)
    ax1.grid(True, linestyle='--', alpha=0.4)
    
    # --- Front Elevation (South Wall) on ax2 ---
    wall_rect = patches.Rectangle((0, 0), wall_width, wall_height, linewidth=2, edgecolor='#1E3A8A', facecolor='#93C5FD', alpha=0.5)
    ax2.add_patch(wall_rect)
    
    # Draw the window if exists
    if has_window:
        w_x = window_offset_x
        w_y = sill_height
        window_rect = patches.Rectangle((w_x, w_y), window_width, window_height, linewidth=2, edgecolor='#DC2626', facecolor='white', hatch='//')
        ax2.add_patch(window_rect)
        
        # Annotations for window
        ax2.annotate(f"{window_width:.1f}m x {window_height:.1f}m", (w_x + window_width/2, w_y + window_height/2), color='#DC2626', weight='bold', ha='center', va='center')
    
    # Base support (Engaste)
    base_rect = patches.Rectangle((-0.5, -0.2), wall_width + 1.0, 0.2, linewidth=1, edgecolor='#4B5563', facecolor='#4B5563', hatch='\\\\')
    ax2.add_patch(base_rect)
    
    ax2.set_xlim(-1.0, wall_width + 1.0)
    ax2.set_ylim(-0.5, wall_height + 1.0)
    ax2.set_aspect('equal')
    ax2.set_xlabel("Length X (m)")
    ax2.set_ylabel("Height Y (m)")
    ax2.set_title(f"Front Elevation: South Wall (H={wall_height:.1f}m)", fontweight='bold', fontsize=14)
    ax2.grid(True, linestyle='--', alpha=0.4)
    
    fig.tight_layout(pad=3.0)
    st.pyplot(fig, use_container_width=True)
    
    
    st.markdown('<div class="section-title">3D Interactive Preview</div>', unsafe_allow_html=True)
    st.info("Browser preview shows detailed South Wall (Meso-model front face) and solid representations for the rest of the 3D Box structure to maintain high framerate performance.")
    fig3d = generate_wall_preview(model_type, wall_width, wall_height, wall_thickness, 
                            building_depth, slab_thickness,
                            window_offset_x, sill_height, window_width, window_height,
                            brick_length, brick_height, brick_depth, mortar_thickness, wythes)
    st.plotly_chart(fig3d, use_container_width=True)

with script_col:
    st.markdown('<div class="section-title">Simulation Scripts Generation</div>', unsafe_allow_html=True)
    
    st.write("Review the parameters and generate the Python scripts for Abaqus and Project Chrono. The generated models will feature a perfectly fixed base (engaste) and facilitate correlation between Abaqus crack mapping and Chrono failure initiation.")
    
    st.markdown("---")
    
    
    st.subheader("1. Finite Element Analysis (CAE)")
    st.info("Generates macro to build the masonry box with Concrete Damage Plasticity (CDP), fixed base support, and applied surface pressure.")
    
    # Abaqus Specific Controls
    st.markdown("**Computational Controls**")
    abq_col1, abq_col2, abq_col3, abq_col4, abq_col5 = st.columns(5)
    with abq_col1:
        def_scale_pct = st.slider("Deformation Scale (%)", min_value=0, max_value=2000, value=100, step=10, help="100% is equivalent to true 1:1 architectural scale. 130% translates to a 1.3x amplification multiplier for Abaqus.")
        def_scale_factor = def_scale_pct / 100.0
    with abq_col2:
        max_num_inc = st.slider("Max Solving Increments", min_value=100, max_value=10000, value=300, step=50, help="Increases the maximum iterative Newton-Raphson attempts for deep failure mapping without the simulation aborting prematurely.")
    with abq_col3:
        cdp_viscosity = st.slider("CDP Viscosity", min_value=0.001, max_value=0.100, value=0.050, step=0.005, format="%.3f", help="Artificial damping for the Concrete Damage Plasticity material model. Higher values delay convergence failure but force physical elasticity.")
    with abq_col4:
        mass_scaling_exp = st.slider("Mass Scaling (Explicit)", min_value=3, max_value=7, value=6, help="Exponent for target Time Increment. E.g., '6' -> 5e-6. Higher values make the simulation faster but introduce massive inertial shock forces in CDP.")
        mass_scaling = 5.0 * (10 ** -mass_scaling_exp)
    with abq_col5:
        num_cpus = st.slider("CPU Cores", min_value=1, max_value=32, value=16 if run_mode == "ROAR" else 2)
    
    # Set Abaqus parameters natively
    params_abaqus = {
        'model_type': model_type,
        'brick_length': brick_length,
        'brick_height': brick_height,
        'brick_depth': brick_depth,
        'mortar_thickness': mortar_thickness,
        'wythes': wythes,
        'slab_thickness': 0.15,
        'mass_scaling': mass_scaling,
        'wall_width': wall_width,
        'wall_height': wall_height,
        'wall_thickness': wall_thickness,
        'has_roof_slab': has_roof_slab,
        'has_window': has_window,
        'window_width': window_width,
        'window_height': window_height,
        'sill_height': sill_height,
        'window_offset_x': window_offset_x,
        'wind_pressure': wind_pressure * 1000.0, # Convert kPa to Pa for Abaqus
        'wind_direction': wind_direction,
        'wind_duration': wind_duration,
        'max_num_inc': max_num_inc,
        'cdp_viscosity': cdp_viscosity,
        'building_depth': building_depth,
        'slab_thickness': slab_thickness,
        'def_scale_factor': def_scale_factor,
        'apply_decay_field': apply_decay_field,
        'num_cpus': num_cpus
    }
    
    abaqus_script_data = generate_abaqus_script(params_abaqus)
    
    st.download_button(
        label="1. Generate & Download Abaqus Macro",
        data=abaqus_script_data,
        file_name="abaqus_macro.py",
        mime="text/plain",
        use_container_width=True
    )
    
    st.markdown("---")
    st.write("**Or run automatically in the background:**")
    abaqus_cmd_path = st.text_input("Abaqus Command Path (if not in System PATH)", value=r"C:\SIMULIA\Commands\abaqus.bat", help="Leave as 'abaqus' if it's already in your Windows Environment Variables.")
    
    button_label = "2. Run Abaqus Simulation Headless" if run_mode == "LOCAL" else "2. Run Abaqus Simulation on ROAR SLURM"
    if st.button(button_label, use_container_width=True, type="primary"):
        with st.spinner("Connecting to Roar Cluster..." if run_mode == "ROAR" else "Executing Abaqus CDP Analysis..."):
            import subprocess
            
            # 1. Ensure directory exists
            run_dir = r"C:\Abaqus_Scripts\Parede_Cenario_01"
            os.makedirs(run_dir, exist_ok=True)
            
            # 2. Get the auto-run script
            abaqus_auto_script_data = generate_abaqus_script(params_abaqus, auto_run=True)
            script_path = os.path.join(run_dir, "abaqus_auto_macro.py")
            with open(script_path, "w", encoding='utf-8', newline='\n') as f:
                f.write(abaqus_auto_script_data)
            
            # 3. Clean up previous output and images 
            for img in ["damaget_result.png", "mises_result.png", "u3_result.png"]:
                img_path = os.path.join(run_dir, img)
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except:
                        pass
                    
            for ext in ['.odb', '.dat', '.msg', '.sta', '.com', '.sim', '.prt', '.log', '.lck']:
                old_file = os.path.join(run_dir, f"MasonryWallJob{ext}")
                if os.path.exists(old_file):
                    try:
                        os.remove(old_file)
                    except:
                        pass
                        
            # Execute based on Environment
            success = False
            
            if run_mode == "ROAR":
                if not psu_user or not psu_pass:
                    st.error("Please provide both PSU Username and Password in the sidebar.")
                    st.stop()
                    
                st.info("Initiating secure tunnel to submit.hpc.psu.edu...")
                from roar_integration import run_on_roar
                status_placeholder = st.empty()
                log_container = st.empty()
                monitor_container = st.empty()
                
                success, msg = run_on_roar(psu_user, psu_pass, script_path, status_placeholder, log_container, monitor_container, num_cpus=num_cpus)
                
                if not success:
                    st.error(f"Penn State Roar Execution Failed: {msg}")
                else:
                    st.success(msg)
            else:
                # 4. Run Abaqus via CLI Local
                executable = abaqus_cmd_path.strip() if abaqus_cmd_path.strip() else "abaqus"
                cmd = [executable, "cae", f"noGUI={script_path}"]
                try:
                    process = subprocess.run(cmd, cwd=run_dir, capture_output=True, text=True, check=True)
                    success = True
                except subprocess.CalledProcessError as e:
                    st.error(f"Abaqus Execution Failed (Exit Code: {e.returncode})")
                    with st.expander("Error Log"):
                        st.code(e.stderr + "\n" + e.stdout)
                except FileNotFoundError:
                    st.error("Abaqus command not found in your system PATH.")

            if success:
                st.markdown("<br><br><hr><br>", unsafe_allow_html=True)
                st.success("Analysis completed! ODB Maps projected below:")
                st.markdown("<br>", unsafe_allow_html=True)
                
                cols = st.columns(3)
                
                try:
                    import PIL.Image
                    
                    if os.path.exists(os.path.join(run_dir, "mises_result.png")):
                        # Verify if it's truly an image or an aborted .dat/.out file disguised as one
                        PIL.Image.open(os.path.join(run_dir, "mises_result.png")).verify()
                        cols[0].image(os.path.join(run_dir, "mises_result.png"), caption="S, Mises Stress")
                        
                    if os.path.exists(os.path.join(run_dir, "damaget_result.png")):
                        cols[1].image(os.path.join(run_dir, "damaget_result.png"), caption="Tensile Damage (DAMAGET)")
                        
                    if os.path.exists(os.path.join(run_dir, "u3_result.png")):
                        cols[2].image(os.path.join(run_dir, "u3_result.png"), caption="Out-of-Plane Disp (U3)")
                        
                except Exception:
                    st.error("🚨 O Solver Explícito do Abaqus explodiu na nuvem do ROAR (Fatal Convergence/Memory Error)!")
                    st.warning("O que fizemos? O Streamlit interceptou o pacote de erro e baixou o arquivo de LOG diretamente pra você ver onde a física abortou:")
                    
                    with open(os.path.join(run_dir, "mises_result.png"), 'r', errors='ignore') as f:
                        log_content = f.read()
                    
                    with st.expander("Abaqus Fatal Log (.dat / .msg) - Últimas Linhas", expanded=True):
                        # Mostrar as últimas 10,000 caracteres do log pesado do Cluster
                        st.code(log_content[-10000:], language='text')
                    
                if not any(os.path.exists(os.path.join(run_dir, img)) for img in ["damaget_result.png", "mises_result.png", "u3_result.png"]):
                    st.warning("Abaqus finished but no expected images were generated. Check the run directory or the log.")
                    if run_mode == "LOCAL" and 'process' in locals():
                        with st.expander("Abaqus Output Log"):
                            st.code(process.stdout)
                            
    if st.button("🖥️ Open in Abaqus/CAE", use_container_width=True):
        import subprocess
        import os
        run_dir = r"C:\Abaqus_Scripts\Parede_Cenario_01"
        odb_path = os.path.join(run_dir, "MasonryWallJob_Final.odb")
        if os.path.exists(odb_path):
            st.success("Opening Abaqus/CAE... (Check your taskbar)")
            executable = abaqus_cmd_path.strip() if abaqus_cmd_path.strip() else "abaqus"
            try:
                subprocess.Popen(f"{executable} viewer odb=MasonryWallJob_Final.odb", cwd=run_dir, shell=True)
            except Exception as e:
                st.error(f"Error launching Abaqus: {e}")
        else:
            st.error("No ODB file found! Please run the simulation first.")
        
    st.markdown('---')
    st.subheader("2. Rigid-Body Dynamics")
    st.write("**Software:** Project Chrono")
    st.write("**Method:** Non-Smooth Contact (NSC)")
    st.write("**Goal:** Simulate discrete collapse mechanism")
    params_chrono = {
        'model_type': model_type,
        'brick_length': brick_length,
        'brick_height': brick_height,
        'brick_depth': brick_depth,
        'mortar_thickness': mortar_thickness,
        'wythes': wythes,
        'wall_height': wall_height, 'wall_width': wall_width, 'wall_thickness': wall_thickness,
        'has_window': has_window, 'window_width': window_width, 'window_height': window_height,
        'sill_height': sill_height, 'window_offset_x': window_offset_x, 
        'wind_pressure': wind_pressure, 'wind_direction': wind_direction,
        'wind_duration': wind_duration,
        'building_depth': building_depth,
        'slab_thickness': slab_thickness,
        'apply_frp': apply_frp if 'apply_frp' in locals() else False
    }
    chrono_script_data = generate_chrono_script(params_chrono)
    
    st.download_button(
        label="Generate & Download PyChrono Script",
        data=chrono_script_data,
        file_name="pychrono_sim.py",
        mime="text/plain",
        use_container_width=True,
        type="primary"
    )
    
    st.markdown("---")
    
    if run_mode == "ROAR":
        st.warning("⚠️ **Project Chrono 3D Real-time Visualization is built for Desktop environments.**\n\nTo run the live brick collapse in the interactive 3D window for your presentation, please switch your Execution Environment (Sidebar) to **Local Desktop**.")
    else:
        st.write("**Or run automatically to display 3D simulation:**")
        chrono_cmd_path = st.text_input("PyChrono Executable Path", value=r"python", help="Command or path for your python environment containing PyChrono.")
        
        if st.button("3. Run PyChrono Simulation Locally", use_container_width=True, type="primary"):
            with st.spinner("Executing Project Chrono 3D Simulation... (Keep the window focused)"):
                import subprocess
                import os
                
                run_dir = r"C:\Abaqus_Scripts\Parede_Cenario_01"
                os.makedirs(run_dir, exist_ok=True)
                
                script_path = os.path.join(run_dir, "pychrono_sim.py")
                with open(script_path, "w", encoding='utf-8', newline='\n') as f:
                    f.write(chrono_script_data)
                    
                try:
                    executable = chrono_cmd_path.strip() if chrono_cmd_path.strip() else "python"
                    cmd = [executable, "pychrono_sim.py"]
                    
                    # We capture output but the Irrlicht window will pop up natively in the OS.
                    # The script blocks Python execution until the Irrlicht window is closed.
                    process = subprocess.run(cmd, cwd=run_dir, capture_output=True, text=True, check=True)
                    st.success("PyChrono simulation completed successfully!")
                except subprocess.CalledProcessError as e:
                    st.error(f"PyChrono Execution Failed (Exit Code: {e.returncode}). Please ensure your executable path is correct and PyChrono is installed.")
                    with st.expander("Error Log"):
                        st.code(e.stderr + "\n" + e.stdout)
                except FileNotFoundError:
                    st.error(f"Executable '{chrono_cmd_path}' not found. Please provide the correct path to your Python-Chrono environment.")


