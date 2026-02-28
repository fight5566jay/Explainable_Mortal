import os
# Set thread limits BEFORE importing any numerical libraries
# This must be done before numpy, sklearn, torch, etc. are imported
_num_threads = '16'  # Default to 16 threads, can be overridden by config later
os.environ['OMP_NUM_THREADS'] = _num_threads
os.environ['MKL_NUM_THREADS'] = _num_threads
os.environ['OPENBLAS_NUM_THREADS'] = _num_threads
os.environ['NUMEXPR_NUM_THREADS'] = _num_threads
os.environ['VECLIB_MAXIMUM_THREADS'] = _num_threads

from datetime import datetime
import argparse
import time
import torch
import numpy as np
import json
import matplotlib.pyplot as plt
import joblib
#from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from activation_extractor import ActivationExtractor
from model import Brain
from config import config
from libriichi.dataset import GameplayLoader
from libriichi.mjai import Concepts
from libriichi.consts import obs_shape
from sklearn.linear_model import LinearRegression, LogisticRegression, Lasso
from sklearn.multioutput import MultiOutputClassifier
from sklearn.model_selection import train_test_split
from glob import glob
from os import path, makedirs
class MortalAnalyzer:
    def __init__(self, model_paths = [], obs_list = [], concepts_list = []):
        # Core member variables
        self.scores: dict[str, dict[str, dict[float]]] = {} # score: float = self.scores['model_name']['concept_name'][block_id]
        self.model_paths: list[str] = model_paths
        # [Question] store the instance of observations and concepts, or their path only?
        self.obs_list: torch.Tensor = obs_list
        self.batched_concepts: list[Concepts] = concepts_list

        # Other necessary settings
        self.device = torch.device(config['control']['device'])
        
        self.rg_models_dir = config['concepts'].get('regression_models_dir', './built/concept_analysis/regression_models')
        self.plots_dir = config['concepts'].get('plots_dir', './built/concept_analysis/plots')
        self.file_batch_size = config['concepts'].get('file_batch_size', 1024)
        self.max_files = config['concepts'].get('max_files', 20)

        # print path in self.model_paths with changing line for debug
        print(f"[MortalAnalyzer.__init__] model_paths:")
        for model_path in self.model_paths:
            print(f"{model_path}")
        
    def load_default_model_paths(self):
        # Let default path be set according to config and remove the substring after the last '/' and add '*.pth'.
        default_dir_path = path.dirname(config['control']['state_file'])
        # Add all test*_mortal.pth files in the directory
        self.model_paths = glob(f"{default_dir_path}/test*_mortal.pth")

    def load_model(self, model_path: str) -> Brain:
        # Load model configuration
        version = config['control']['version']
        conv_channels = config['resnet']['conv_channels']
        num_blocks = config['resnet']['num_blocks']


        # Load the trained model
        print("Loading trained model...")
        model = Brain(version=version, conv_channels=conv_channels, num_blocks=num_blocks)
        
        try:
            state = torch.load(model_path, weights_only=True, map_location=self.device)
            model.load_state_dict(state['mortal'])
            model.eval()
            print(f"✓ Model loaded successfully (steps: {state['steps']:,})")
        except FileNotFoundError:
            print(f"⚠ Model file not found: {model_path}")
            print("Using randomly initialized model for demonstration")
            model.eval()

        return model
    
    def load_games_from_file(self, files: list[str] = [], batch_size=8, max_files=3, random_seed=None) -> tuple[torch.Tensor, list[Concepts]]:
        """
        Load real observations and concepts from dataset .json.gz files.
        
        Args:
            files: List of dataset files to load
            batch_size: Number of observations to load
            max_files: Maximum number of files to read
        Returns:
            Tuple of (observations_tensor, concepts_list)
        """
        print("Loading real observations from dataset...")
    
        all_files = files
        if not files:
            # Get dataset file patterns from config
            dataset_globs = config['dataset']['globs']
            version = config['control']['version']
            
            # Find available files
            all_files = []
            for pattern in dataset_globs:
                files = glob(pattern, recursive=True)
                all_files.extend(files)
        
        if not all_files:
            print(f"⚠ No dataset files found matching patterns: {dataset_globs}")
            print("Falling back to random observations")
            return torch.randn(batch_size, *obs_shape(version)), []
        
        # Limit number of files to process
        # files_to_load = all_files[:max_files]

        # random pick max_files from all_files (using random seed for reproducibility)
        if random_seed is not None:
            np.random.seed(random_seed)
        np.random.shuffle(all_files)
        files_to_load = all_files[:max_files]

        print(f"  Found {len(all_files)} total files, using {len(files_to_load)}")
        print(f"\n  Loading from files:")
        for i, f in enumerate(files_to_load, 1):
            print(f"    {i}. {f}")
        
        # Load observations using GameplayLoader
        loader = GameplayLoader(
            version=version,
            oracle=False,
            player_names=[],
            excludes=[],
            augmented=False,
        )
        
        observations = []
        concepts_list = []
        files_loaded = 0
        BATCH_SIZE_LOADED_FILES = 10  # Number of files to load before processing batch (to avoid loading too many files at once)
        
        try:
            # Load data in batches of BATCH_SIZE_LOADED_FILES files at a time
            file_idx = 0
            while file_idx < len(files_to_load) and len(observations) < batch_size:
                # Get next batch of files
                batch_end_loaded_files = min(file_idx + BATCH_SIZE_LOADED_FILES, len(files_to_load))
                files_batch = files_to_load[file_idx:batch_end_loaded_files]
                
                # Load this batch of files
                data = loader.load_gz_log_files(files_batch)
                
                for file in data:
                    files_loaded += 1
                    for game in file:
                        obs_list = game.take_obs()
                        concepts = game.take_concepts_list()
                        
                        # Convert to tensor and add to collection
                        for obs_np, concept in zip(obs_list, concepts):
                            if len(observations) >= batch_size:
                                break
                            observations.append(torch.from_numpy(obs_np))
                            concepts_list.append(concept)
                        
                        if len(observations) >= batch_size:
                            break
                    
                    if len(observations) >= batch_size:
                        break
                
                file_idx = batch_end_loaded_files
            
            if observations:
                # Stack observations into batch
                obs_batch = torch.stack(observations[:batch_size])
                concepts_batch = concepts_list[:batch_size]
                print(f"\n  ✓ Loaded {len(obs_batch)} real observations and concepts from {files_loaded} files")
                return obs_batch, concepts_batch
            else:
                print("  ⚠ No observations loaded, using random data")
                return torch.randn(batch_size, *obs_shape(version)), []
                
        except Exception as e:
            print(f"  ⚠ Error loading observations: {e}")
            print("  Falling back to random observations")
            return torch.randn(batch_size, *obs_shape(version)), []
        
    def write_scores_to_file(self, output_path: str = None) -> None:
        if output_path is None:
            output_path = config['concepts']['analysis_file']
        print(f"\nWriting scores to file: {output_path}")

        try:
            with open(output_path, 'w') as f:
                json.dump(self.scores, f, indent=4)
            print(f"Scores written to {output_path}")
        except Exception as e:
            print(f"  ⚠ Error writing scores to file: {e}")

    def read_scores_from_file(self, input_path: str = None) -> None:
        if input_path is None:
            input_path = config['concepts']['analysis_file']
        print(f"\nReading scores from file: {input_path}")

        try:
            with open(input_path, 'r') as f:
                self.scores = json.load(f)
            print(f"Scores loaded from {input_path}")
        except Exception as e:
            print(f"  ⚠ Error reading scores from file: {e}")

    def get_regression_score(self
                             , actv: torch.Tensor
                             , batched_cc: list
                             , train_test_ratio: float = 0.2
                             , random_state: int = None
                             , is_save_rg_model: bool = True
                             , rg_model_path: str = None
                             , load_existed_model: bool = True) -> float:
        score = float('nan')
        if batched_cc is None or len(batched_cc) == 0:
            print("  No concept data provided for regression.")
            return score
        if rg_model_path is None:
            print("  rg_model_path should not be None.")
            return score

        # Convert activations to numpy and flatten it to shape: [batch_size, features]
        act_flat = actv.cpu().numpy().reshape(actv.size(0), -1)
        print(f"  Activation shape: {actv.shape} -> Flattened: {act_flat.shape}")

        # Determine if boolean (use logistic) or numeric (use linear)
        is_bool = isinstance(batched_cc[0], (bool, np.bool_))
        is_num = isinstance(batched_cc[0], (float, int))
        is_list = isinstance(batched_cc[0], list)

        if is_bool:
            y = np.array(batched_cc)
            # convert to 0/1
            y = y.astype(int)
            regression_model = LogisticRegression(
                max_iter=1000,
                penalty='l1', 
                solver='liblinear', 
                C=1.0,
            )
        elif is_num:
            y = np.array(batched_cc)
            y = y.astype(float)
            #regression_model = LinearRegression()
            regression_model = Lasso(alpha=0.1, max_iter=4000)  # alpha controls regularization strength
        elif is_list:
            print(f" list element type: {type(batched_cc[0][0])}, len = {len(batched_cc[0])}")
            print(f"  Concept data: {batched_cc[0]}")

            assert(len(batched_cc[0]) > 0), "Only single-element lists are supported for concept regression."
            if isinstance(batched_cc[0][0], (bool, np.bool_)):
                # keep the shape as 2D but change bool to int
                y = np.array([ [int(val) for val in sublist] for sublist in batched_cc])
                print(f"  Converted boolean list to int array with shape: {y.shape}")
                print(f"  result int array: {y}")
                # Use MultiOutputClassifier for multilabel classification
                regression_model = MultiOutputClassifier(LogisticRegression(
                    max_iter=1000,
                    penalty='l1', 
                    solver='liblinear', 
                    C=1.0,
                ))
            elif isinstance(batched_cc[0][0], (int, float)):
                # keep the shape as 2D but change to float
                y = np.array([ [float(val) for val in sublist] for sublist in batched_cc])
                print(f"  Converted numeric list to float array: {y}")
                #regression_model = LinearRegression()
                regression_model = Lasso(alpha=0.1, max_iter=4000)  # alpha controls regularization strength
            else:
                print(f"  Unsupported concept data type for regression: {type(batched_cc[0])}, list element type: {type(batched_cc[0][0])}")
                print(f"  Concept data: {batched_cc[0][0]}")
                exit(0)
        else:
            print(f"  Unsupported concept data type for regression: {type(batched_cc[0])}")
            print(f"  Concept data: {batched_cc[0]}")
            exit(0)

        random_state = 556 if random_state is None else random_state
        X_train, X_test, y_train, y_test = train_test_split(
            act_flat, y, test_size=train_test_ratio, random_state=random_state
        )

        is_load_existed_model = False
        #Try to load existing model if available
        if load_existed_model and path.exists(rg_model_path):
            print(f"  Loading existing regression model from {rg_model_path}")
            rg_model = self.load_regression_model(rg_model_path)
            if rg_model is not None:
                regression_model = rg_model
                is_load_existed_model = True

        #If loading failed or no existing model, fit a new one
        if not is_load_existed_model:
            print("  Failed to load existing regression model. Start training a new one.")
            try:
                regression_model.fit(X_train, y_train)
            except Exception as e:
                print(f"  Failed to fit: {e}")
                # [TODO] how to handle this case? (Lack data for some classes)
                # If it is MultiOutputClassifier, just return average score of other classifiers that are successfully trained
                # If all fail, return NaN
                return float('nan')

        score = regression_model.score(X_test, y_test)
        print(f"  regression_model.score: {score:.4f}")

        if not is_load_existed_model and is_save_rg_model and rg_model_path is not None:
            #print(f"  Saving regression model to {rg_model_path}")
            self.save_regression_model(regression_model, rg_model_path)

        return score
    
    def save_regression_model(self, model: LogisticRegression | LinearRegression | Lasso, output_path: str) -> None:
        """
        Save the regression model to a file using joblib.
        
        Args:
            model: The regression model to save
            output_path: Path to save the model
        """
        try:
            joblib.dump(model, output_path)
            print(f"  Regression model saved to {output_path}")
        except Exception as e:
            print(f"  Failed to save regression model: {e}")

    def load_regression_model(self, input_path: str) -> LogisticRegression | LinearRegression | Lasso | None:
        """
        Load a regression model from a file using joblib.
        
        Args:
            input_path: Path to load the model from
        """
        try:
            model = joblib.load(input_path)
            print(f"  Regression model loaded from {input_path}")
            return model
        except Exception as e:
            print(f"  Failed to load regression model: {e}")
            return None
        
    def _get_rg_model_name(self, model_name: str, cc_field: str, block_id: int) -> str:
        model_name = path.basename(model_name).replace('.pth', '')
        return f"Model_{model_name}_Concept_{cc_field}_Block_{block_id}"

    def gen_www_plot(self, concept_name: str, output_path: str = None):
        """
        Generate 3D surface plot showing regression scores across blocks and training steps.
        
        Args:
            concept_name: Name of the concept to plot (e.g., 'is_menzen', 'doras_owned')
            output_path: Path to save the plot. If None, displays interactively.
            
        Returns:
            matplotlib figure object
        """
        if not self.scores:
            print("No scores available. Run analysis first.")
            return None
            
        # Extract training steps from model names (format: test<steps>_mortal.pth)
        training_steps = []
        models_data = []
        
        for model_name in sorted(self.scores.keys()):
            try:
                # Extract step number from filename like "test12345_mortal.pth"
                step = int(model_name.replace('test', '').replace('_mortal.pth', ''))
                training_steps.append(step)
                models_data.append(model_name)
            except ValueError:
                continue
        
        if not training_steps:
            print("No valid model checkpoints found.")
            return None
            
        if concept_name not in self.scores[models_data[0]]:
            print(f"Concept '{concept_name}' not found. Available: {list(self.scores[models_data[0]].keys())}")
            return None
        
        # Get block IDs from first model
        block_ids = sorted(self.scores[models_data[0]][concept_name].keys())
        
        # Create meshgrid for 3D plot
        X, Y = np.meshgrid(training_steps, block_ids)
        Z = np.zeros_like(X, dtype=float)
        
        # Fill Z with scores
        for i, block_id in enumerate(block_ids):
            for j, model_name in enumerate(models_data):
                score = self.scores[model_name][concept_name].get(block_id, np.nan)
                Z[i, j] = score if not np.isnan(score) else 0.0
        
        # Create 3D plot
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # Plot surface with fixed color scale from 0 to 1
        surf = ax.plot_surface(X, Y, Z, cmap=cm.plasma, 
                               linewidth=0, antialiased=True, alpha=0.9,
                               vmin=0, vmax=1)
        
        # Customize plot
        ax.set_xlabel('Training steps', fontsize=12, labelpad=10)
        ax.set_ylabel('Block', fontsize=12, labelpad=10)
        ax.set_zlabel('Test accuracy', fontsize=12, labelpad=10)
        ax.set_title(f"{concept_name}", fontsize=14, pad=20)
        
        # Set z-axis limits
        ax.set_zlim(0, 1)
        
        # Reverse x-axis and y-axis to show training steps in descending order
        ax.invert_xaxis()
        ax.invert_yaxis()

        # Add colorbar with fixed range
        fig.colorbar(surf, shrink=0.5, aspect=5)
        
        # Adjust viewing angle
        ax.view_init(elev=25, azim=45)
        
        # Save or show
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {output_path}")
        else:
            plt.show()
        
        return fig
    
    def gen_all_concept_plots(self, output_dir: str = None):
        """
        Generate 3D plots for all concepts.
        
        Args:
            output_dir: Directory to save plots
        """
        
        if not self.scores:
            print("No scores available. Run analysis first.")
            return

        if output_dir is None:
            output_dir = self.plots_dir
        makedirs(output_dir, exist_ok=True)
        
        # Get all concept names from first model
        first_model = list(self.scores.keys())[0]
        concept_names = list(self.scores[first_model].keys())
        
        print(f"\nGenerating 3D plots for {len(concept_names)} concepts...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # make dir
        output_dir = path.join(output_dir, timestamp)
        makedirs(output_dir, exist_ok=True)

        for concept_name in concept_names:
            output_path = path.join(output_dir, f"{concept_name}_3d_{timestamp}.png")

            print(f"  Creating plot for: {concept_name}")
            self.gen_www_plot(concept_name, output_path)
            plt.close()  # Close to free memory
        
        print(f"All plots saved to {output_dir}")
    
    def run(self, is_save_rg_model: bool = True, load_regression_models: bool = False, activation_interval: int = 1):
        # Load observations and concepts from game files
        self.obs_list, self.batched_concepts = self.load_games_from_file(batch_size=self.file_batch_size, max_files=self.max_files, random_seed=556)
        self.obs_list = self.obs_list.to(self.device)
        print(f"Observations tensor shape: {self.obs_list.shape}")
        print(f"Number of concepts loaded: {len(self.batched_concepts)}")

        # [Preprocessing]
        # Ensure regression models directory exists
        if is_save_rg_model:
            makedirs(self.rg_models_dir, exist_ok=True)
        
        # [Main process]
        # Load models
        if not self.model_paths:
            self.load_default_model_paths()

        if len(self.model_paths) == 0:
            print("⚠ No model paths provided or found. Please check the configuration and ensure model files are available.")
            return
        
        print(f"Found {len(self.model_paths)} model(s) to analyze.")
        # If not loading existing regression models, move them to a new directory named by their timestamp
        if not load_regression_models and path.exists(self.rg_models_dir):
            print("load_regression_models is set to False. Storing existing regression models to new directory.")
                
            existing_models = glob(path.join(self.rg_models_dir, "**", "*.joblib"), recursive=True)
            print(f"\nFound {len(existing_models)} existing regression model(s) in {self.rg_models_dir}.")

            if existing_models:
                # Let timestamp be the time that the oldest regression model in rg_models_dir was trained
                oldest_model = min(existing_models, key=os.path.getctime)
                timestamp = datetime.fromtimestamp(os.path.getctime(oldest_model)).strftime("%Y%m%d_%H%M%S")
                # Make dir for existing models with this timestamp and move them there
                dir_for_existing_rg_models = self.rg_models_dir + "_" + timestamp
                makedirs(dir_for_existing_rg_models, exist_ok=True)

                print(f"\nMoving existing regression models to directory: {dir_for_existing_rg_models}")
                # Move all existing models (including those in subdirectories) to the timestamp directory
                for existing_model in existing_models:
                    # Get relative path from rg_models_dir to preserve directory structure
                    rel_path = path.relpath(existing_model, self.rg_models_dir)
                    target_path = path.join(dir_for_existing_rg_models, rel_path)
                    # Create target subdirectory if needed
                    makedirs(path.dirname(target_path), exist_ok=True)
                    os.rename(existing_model, target_path)
                    print(f"  Moved {rel_path} to {dir_for_existing_rg_models}")
        
        # Analyze each model
        for model_path in self.model_paths:
            # abstract model (uint) from model_path (format: .../test<model>_mortal.pth)
            # model_id = int(path.basename(model_path).split('_')[0].replace('test', ''))
            model_name = path.basename(model_path)
            self.scores[model_name] = {}

            print(f"\nAnalyzing model: {model_path}")
            model = self.load_model(model_path).to(self.device)

            # Prepare batched_concept for each concept field
            # Get all concept field names dynamically from the first concept
            if self.batched_concepts is not None:
                concept_fields = list(self.batched_concepts[0].to_dict().keys())
                print(f"\nConcept fields to regress: {concept_fields}")
            else:
                concept_fields = []
    
            # Get activations (with context manager __enter__ and __exit__ in ActivationExtractor)
            with ActivationExtractor(model) as extractor:
                with torch.no_grad():
                    output = model(self.obs_list)
                activations = extractor.get_activations(interval=activation_interval)
            print("\nExtracted activations:")
            # Print the name of each activation
            for actv_name, actv in activations.items():
                print(f"{actv_name}\n")

            # For each concept and each block, build a regression model and acquire the score
            for cc_field in concept_fields:
                #if cc_field != 'doras_owned':
                    # [Testing] Skip other concepts for now
                    #continue

                self.scores[model_name][cc_field] = {}

                # Get batched value of a single concept
                batched_cc = [concepts.to_dict()[cc_field] for concepts in self.batched_concepts]
                print(f"\nRegressing Concept: {cc_field} (Samples: {len(batched_cc)})")
                
                for actv_name, actv in activations.items():
                    # abstract block_id (uint) from activations key (format: resblock_<block_id>)
                    block_id = int(actv_name.split('_')[1])
                    actv_tensor = actv.to(self.device)
                    print(f"  Processing Block {block_id}. ")
                    print(f"  Activation tensor shape: {actv_tensor.shape}")

                    rg_model_name = self._get_rg_model_name(model_name, cc_field, block_id)
                    # Organize models by concept in subdirectories
                    concept_dir = path.join(self.rg_models_dir, cc_field)
                    if is_save_rg_model:
                        makedirs(concept_dir, exist_ok=True)
                    rg_model_path = path.join(concept_dir, f"{rg_model_name}.joblib")
                    self.scores[model_name][cc_field][block_id] = self.get_regression_score(actv_tensor
                                                                                            , batched_cc
                                                                                            , is_save_rg_model=is_save_rg_model
                                                                                            , rg_model_path=rg_model_path
                                                                                            , load_existed_model=load_regression_models
                                                                                            )
                    print(f"  {rg_model_name}: Score = {self.scores[model_name][cc_field][block_id]:.4f}")
            
            # Explicit cleanup before next model iteration
            del model, output, activations
            if self.device.type == 'cuda':
                torch.cuda.empty_cache()
        
        # Write scores to file
        self.write_scores_to_file()

        # Generate 3D plots if multiple models analyzed
        if len(self.model_paths) > 1:
            print("\nGenerating 3D visualization plots...")
            self.gen_all_concept_plots()

        # Currently done.
        print("\nAnalysis complete.")


if __name__ == '__main__':
    # read the flag '--load_rg_models' from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--train_new_rg_models', default=False, action='store_true', help='Train new regression models instead of loading existing ones')
    args = parser.parse_args()

    #analyzer = MortalAnalyzer()
    #analyzer = MortalAnalyzer(model_paths = glob("/workspace/mortal/built/models/test*_mortal.pth"))
    analyzer = MortalAnalyzer(model_paths = glob("/workspace/mortal/built/models_for_concepts/test*_mortal.pth"))
    analyzer.run(load_regression_models = not args.train_new_rg_models, activation_interval = 5)