# density_planner

Official Code for "Density Planner: Minimizing Collision Risk in Motion Planning with Dynamic Obstacles using Density-based Reachability"

python -m gps_planning.plan_gps_motion --mp_setting gps --gps_real_env False

## GPS Planner
1. GPS planner COMMAND
```bash
python -m gps_planning.plan_gps_motion --mp_setting gps
```

For real enviornment testing
```bash
python -m gps_planning.plan_gps_motion --mp_setting gps --gps_real_env False
```

2. MPNET
training obs

```bash
python -m MPNet.AE.CAE_obs
python -m MPNet.AE.CAE_gps
```

for cluster
conda install -c conda-forge texlive-core

parameter list

```
parser.add_argument('--environment_size', type=list, default=[-12, 12, -30, 10])
parser.add_argument('--mp_gaussians', type=int, default=5)
parser.add_argument('--grid_wide', type=float, default=0.1)
parser.add_argument('--mp_sample_size', type=int, default=500)
```

## Installation
1. clone the project
```bash
git clone https://github.com/MIT-REALM/density_planner.git
```

2. Create and activate new environment
```bash
conda create --name gps python=3.8
conda activate gps
```

3. Install requirements from "requirements.txt"
```bash
pip install -r requirements.txt
```

## Usage for Motion Planning of Autonomous Vehicles
specify motion planning methods in "motion_planning/plan_motion.py":

### To compare the optimization methods: 
```bash
python -m motion_planning.plan_motion --mp_setting ablation
```

### To compare all motion planning methods in artificially generated environments:
```bash
python -m motion_planning.plan_motion --mp_setting artificial --mp_plot True --mp_plot_cost True --mp_plot_envgrid True
```

### To compare motion planning methods in environments generated from real-world environments:
```bash
python -m motion_planning.plan_motion --mp_setting real
```

### To create custom comparison:
1. define optimization and motion planning methods in "motion_planning/plan_motion.py", line 34 and line 37  
2. start the motion planner with custom options:
```
python -m motion_planning.plan_motion [--mp_name NAME] [--mp_setting SETTING] [--random_seed SEED] [--mp_use_realEnv REAL]  
               [--mp_stationary STAT] [--mp_num_envs NUM_ENVS] [--mp_num_initial NUM_INITIAL] [--mp_recording RECORDING]  
               [--mp_plot PLOT] [--mp_plot_cost PLOT_C] [--mp_plot_envgrid PLOT_E] [--mp_plot_final PLOT_F] [--mp_plot_traj PLOT_T]
             
optional arguments:
  --mp_name NAME            Name for the logging folder (default: "test)
  --mp_setting SETTING      Configuration to reproduce the results from the paper (default: "custom")  
                              "ablation" for comparison of optimization methods  
                              "artificial" for comparison of all motion planning methods in artificially generated environments  
                              "real" for  motion planning methods in environments generated from real-world environments  
                              "custom" for custom configuration  
  --random_seed SEED        Random seed which is used for generating the motion planning task and drawing the initial state (default: 0)
  --mp_use_realEnv REAL     True if real-world environments should be used (False for SETTING="artificial", True for SETTING="real", default: False)  
  --mp_stationary STAT      True if stationary environments should be used (default: False)  
  --mp_num_envs NUM_ENVS    Number of environments which should be tested (default: 10)  
  --mp_num_initial NUM_ENVS    Number of different initial states which are tested in each environment (default: 1)  
  --mp_recording RECORDING  Recording of the inD dataset which is used if REAL=True (default: 26)  
  --mp_plot PLOT            True if intermdiate Trajectories during optimization should be plotted (default: False)
  --mp_plot_cost PLOT_C     True if cost curves from gradient-based optimization should be plotted (default: False)
  --mp_plot_envgrid PLOT_E  True if occupation map should be plotted (default: False)
  --mp_plot_final PLOT_F    True if final optimized/ planned trajectory should be plotted (default: True)
  --mp_plot_traj PLOT_T     True if final optimized/ planned trajectories of all motion planners should be plotted in one plot (default: False)
```

## Usage for Other Systems
1. train contraction controller for the new system with "https://github.com/sundw2014/C3M", and save controller and model in "data/trained_controller/"  
2. define the dynamics of the new system analog to "systems/system_CAR.py" and put path to the trained controller in function "system.load_controller"  
3. generate trainings data  
  a) generate lots of raw data by solving the Liouville equation with "data_generation/compute_rawdata.py"   
  b) create trainings and validation dataset with "data_generation/create_dataset.py" by setting "args.nameend_rawdata" to the name of the rawdata folder
4. train density predictor for the new system with "density_training/train_density.py"  
    (set "args.nameend_TrainDataset" to the name of your trainings dataset, set "args.nameend_ValDataset" to the name of your validation dataset,
    specify hyperparmaters for the training in hyperparms.py) 
5. do motion planning as described in the previous section  
    (set "args.name_pretrained_nn" to the name of the trained density predictor)

