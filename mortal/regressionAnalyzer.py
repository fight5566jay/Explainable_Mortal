import argparse
import glob
import numpy as np
import joblib
from sklearn.linear_model import LinearRegression, LogisticRegression, Lasso
from sklearn.multioutput import MultiOutputClassifier


class RegressionAnalyzer:
    def __init__(self, mortal_path_list = [], regression_path_list = []):
        """
        Initialize the RegressionAnalyzer.
        
        Args:
            mortal_list: List of mortal models (not used yet)
            regression_list: List of regression models (sklearn models)
        """
        self.mortal_list = mortal_path_list
        self.regression_list = regression_path_list
        #self.mortal = Brain(...)
        #self.regression = None

    def get_zero_weight_count_in_regression(self, regression_model=None):
        """
        Calculate the count of zero weights and total weight count in a regression model.
        
        Args:
            regression_model: A sklearn regression model (LinearRegression, LogisticRegression, Lasso, etc.)
                             If None, uses the first model from regression_list
        
        Returns:
            tuple: (zero_weight_count, total_weight_count)
                - zero_weight_count (int): Count of zero weights (weights with absolute value < 1e-10)
                - total_weight_count (int): Total number of weights in the model
        """
        if regression_model is None:
            if not self.regression_list:
                return 0, 0
            regression_model = self.regression_list[0]
        
        zero_weight_count = 0
        total_weight_count = 0
        
        # Handle MultiOutputClassifier
        if isinstance(regression_model, MultiOutputClassifier):
            for estimator in regression_model.estimators_:
                if hasattr(estimator, 'coef_'):
                    coef = estimator.coef_
                    total_weight_count += coef.size
                    zero_weight_count += np.sum(np.abs(coef) < 1e-10)
        # Handle standard sklearn models with coef_ attribute
        elif hasattr(regression_model, 'coef_'):
            coef = regression_model.coef_
            total_weight_count = coef.size
            zero_weight_count = np.sum(np.abs(coef) < 1e-10)
        else:
            print(f"Warning: Model {type(regression_model)} doesn't have coef_ attribute")
            
        return int(zero_weight_count), int(total_weight_count)
    
    def get_weight_l1_sum_in_regression(self, regression_model=None):
        """
        Calculate the sum of all weights and total weight count in a regression model.
        
        Args:
            regression_model: A sklearn regression model (LinearRegression, LogisticRegression, Lasso, etc.)
                             If None, uses the first model from regression_list
        
        Returns:
            tuple: (weight_sum, total_weight_count)
                - weight_sum (float): Sum of all weights
                - total_weight_count (int): Total number of weights in the model
        """
        if regression_model is None:
            if not self.regression_list:
                return 0.0, 0
            regression_model = self.regression_list[0]
        
        weight_sum = 0.0
        total_weight_count = 0
        
        # Handle MultiOutputClassifier
        if isinstance(regression_model, MultiOutputClassifier):
            for estimator in regression_model.estimators_:
                if hasattr(estimator, 'coef_'):
                    coef = estimator.coef_
                    total_weight_count += coef.size
                    weight_sum += np.sum(np.abs(coef))
        # Handle standard sklearn models with coef_ attribute
        elif hasattr(regression_model, 'coef_'):
            coef = regression_model.coef_
            total_weight_count = coef.size
            weight_sum = np.sum(np.abs(coef))
        else:
            print(f"Warning: Model {type(regression_model)} doesn't have coef_ attribute")
            
        return float(weight_sum), int(total_weight_count)
    
    def load_regression_model(self, model_path):
        """
        Load a regression model from file.
        
        Args:
            model_path: Path to the saved regression model (.joblib file)
        
        Returns:
            The loaded regression model or None if loading fails
        """
        try:
            model = joblib.load(model_path)
            return model
        except Exception as e:
            print(f"Failed to load regression model from {model_path}: {e}")
            return None
    
    def load_mortal(self, mortal_path):
        """
        Load mortal model from file.
        
        Args:
            mortal_path: Path to the mortal model file
        """
        # TODO: Implement mortal model loading
        pass

    def run(self, output_file="output_RegressionAnalyzer.txt"):
        """
        Run the regression analysis and write results to a file.
        
        Args:
            output_file: Path to the output file (default: "output_RegressionAnalyzer.txt")
        """
        # First pass: collect statistics for each concept
        concept_stats = {}
        rg_model_stats = {}
        
        for rg_model_path in self.regression_list:
            rg_model = self.load_regression_model(rg_model_path)
            if rg_model is not None:
                # Extract concept name from path
                try:
                    rg_model_name = rg_model_path.split('/')[-1].split('.')[0]
                    concept_name = rg_model_path.split('Concept_')[-1].split('_Block_')[0]
                except:
                    rg_model_name = "Unknown"
                    concept_name = "Unknown"
                
                zero_count, total_count = self.get_zero_weight_count_in_regression(rg_model)
                weight_l1_sum, total_weights = self.get_weight_l1_sum_in_regression(rg_model)
                
                # zero_ratio = zero_count / total_count if total_count > 0 else 0.0

                if rg_model_name not in rg_model_stats:
                    rg_model_stats[rg_model_name] = {
                        'zero_count': 0,
                        'weight_l1_sums': 0.0,
                        'total_weight_count': 0,
                        'concept_name': concept_name,
                        'training_step': rg_model_name.split('test')[-1].split('_')[0] if 'test' in rg_model_name else "Unknown",
                        'block': rg_model_name.split('Block_')[-1].split('.')[0] if 'Block_' in rg_model_name else "Unknown"
                    }
                rg_model_stats[rg_model_name]['zero_count'] = zero_count
                rg_model_stats[rg_model_name]['weight_l1_sums'] = weight_l1_sum
                rg_model_stats[rg_model_name]['total_weight_count'] = total_weights
                if concept_name not in concept_stats:
                    concept_stats[concept_name] = {
                        'zero_count': 0,
                        'weight_l1_sums': 0.0,
                        'count': 0,
                        'total_weight_count': 0
                    }
                concept_stats[concept_name]['zero_count'] += zero_count
                concept_stats[concept_name]['weight_l1_sums'] += weight_l1_sum
                concept_stats[concept_name]['count'] += 1
                concept_stats[concept_name]['total_weight_count'] = total_weights
        
        # Write results to file
        with open(output_file, 'w') as f:
            f.write(f"Regression Analysis Results\n")
            f.write(f"Total models to analyze: {len(self.regression_list)}\n")
            f.write("=" * 80 + "\n\n")
            
            # Write average statistics per concept
            f.write("Average Statistics by Concept:\n")
            f.write("=" * 80 + "\n")
            for concept_name in sorted(concept_stats.keys()):
                stats = concept_stats[concept_name]
                avg_zero_count = stats['zero_count'] / stats['count'] if stats['count'] > 0 else 0.0
                avg_weight_l1_sum = stats['weight_l1_sums'] / stats['count'] if stats['count'] > 0 else 0.0
                avg_zero_ratio = avg_zero_count / stats['total_weight_count'] if stats['total_weight_count'] > 0 else 0.0
                avg_weight_l1_sum_ratio_nonzero = avg_weight_l1_sum / (stats['total_weight_count'] - stats['zero_count']) if (stats['total_weight_count'] - stats['zero_count']) > 0 else 0.0

                f.write(f"Concept: {concept_name}\n")
                f.write(f"  Number of models: {stats['count']}\n")
                f.write(f"  Average Zero Weight Ratio: {avg_zero_ratio*100:.2f}%\n")
                f.write(f"  Average Weight L1 Sum: {avg_weight_l1_sum:.6f}\n")
                f.write(f"  Average Weight L1 Sum Ratio: {avg_weight_l1_sum_ratio_nonzero:.6f}\n")
                f.write(f"  Total Weight Count: {stats['total_weight_count']}\n")
                f.write("-" * 80 + "\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("Detailed Model Information:\n")
            f.write("=" * 80 + "\n\n")

            for rg_model_name in sorted(rg_model_stats.keys()):
                stats = rg_model_stats[rg_model_name]
                zero_count = stats['zero_count']
                weight_l1_sum = stats['weight_l1_sums']
                zero_ratio = zero_count / stats['total_weight_count'] if stats['total_weight_count'] > 0 else 0.0
                weight_l1_sum_ratio_nonzero = weight_l1_sum / (stats['total_weight_count'] - zero_count) if (stats['total_weight_count'] - zero_count) > 0 else 0.0

                f.write(f"Model: {rg_model_name}\n")
                f.write(f"  Concept: {stats['concept_name']}\n")
                f.write(f"  Training Step: {stats['training_step']}\n")
                f.write(f"  Block: {stats['block']}\n")
                f.write(f"  Zero Weight Ratio: {zero_ratio*100:.2f}%\n")
                f.write(f"  Weight L1 Sum: {weight_l1_sum:.6f}\n")
                f.write(f"  Weight L1 Sum Ratio (Non-zero): {weight_l1_sum_ratio_nonzero:.6f}\n")
                f.write(f"  Total Weight Count: {stats['total_weight_count']}\n")
                f.write("-" * 80 + "\n")
        
        print(f"\nResults written to {output_file}")

if __name__ == '__main__':
    # read the flag '--load_rg_models' from command line arguments
    parser = argparse.ArgumentParser()
    # parser.add_argument('--train_new_rg_models', default=False, action='store_true', help='Train new regression models instead of loading existing ones')
    args = parser.parse_args()

    # Load all regression models from specific directory
    regression_path_list = glob.glob("built/concept_analysis/regression_models/**/*.joblib", recursive=True)
    print(f"Found {len(regression_path_list)} regression models")

    analyzer = RegressionAnalyzer(regression_path_list=regression_path_list)
    analyzer.run()