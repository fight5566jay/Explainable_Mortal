"""
Utility for extracting internal activations from ResBlocks using forward hooks.
"""

import torch
import numpy as np
from typing import Dict, List, Optional
from model import Brain, ResBlock


class ActivationExtractor:
    """
    Extract internal activations from ResBlocks in the Brain model.
    
    Usage:
        model = Brain(version=4, conv_channels=192, num_blocks=40)
        model.load_state_dict(state_dict)
        model.eval()
        
        extractor = ActivationExtractor(model)
        extractor.register_hooks()
        
        with torch.no_grad():
            output = model(obs)
        
        activations = extractor.get_activations()
        print(f"ResBlock 0 output shape: {activations['resblock_0'].shape}")
        
        extractor.remove_hooks()
    """
    
    def __init__(self, model: Brain):
        """
        Initialize the activation extractor.
        
        Args:
            model: Brain model instance
        """
        self.model = model
        self.activations: Dict[str, torch.Tensor] = {} 
        # Though using Dict for activations is more flexible and readable, 
        # I think using List is also fine and more simple if only observing ResBlocks (by sctang 251029)
        self.hooks = []
        self.block_name_root = 'resblock_'
        
    def _make_hook(self, name: str):
        """
        Create a hook function that stores activations.
        Need to return a function including "module", "input", "output" arguments.
        """
        def hook(module, input, output):
            # Detach and clone to avoid gradient issues
            self.activations[name] = output.detach().clone()
        return hook
    
    def register_hooks(self, block_indices: Optional[List[int]] = None):
        """
        Register forward hooks to capture ResBlock outputs.
        
        Args:
            block_indices: List of block indices to hook. If None, hooks all blocks.
        """
        # Clear any existing hooks
        self.remove_hooks()
        self.activations = {}
        
        # Get the ResNet encoder
        encoder = self.model.encoder
        
        # Access the blocks from the sequential network
        # The structure is: [initial_conv, block_0, block_1, ..., block_39, final_layers]
        blocks = []
        for name, module in encoder.net.named_children():
            # ResBlocks are the modules after the initial conv layer
            if isinstance(module, ResBlock):  # Check if it's a ResBlock
                blocks.append(module)
        
        # If no specific indices provided, hook all blocks
        if block_indices is None:
            block_indices = list(range(len(blocks)))
        
        # Register hooks for specified blocks
        for i in block_indices:
            if i < len(blocks):
                hook = blocks[i].register_forward_hook(
                    self._make_hook(f'{self.block_name_root}{i}')
                )
                self.hooks.append(hook)
                
        print(f"Registered hooks for {len(self.hooks)} ResBlocks")
        
    def remove_hooks(self):
        """Remove all registered hooks."""
        for hook in self.hooks:
            hook.remove()
        self.hooks = []
        
    def get_activations(self, clear: bool = True, interval: int = 1) -> Dict[str, torch.Tensor]:
        """
        Get the stored activations.
        
        Args:
            clear: If True, clear the activations after returning them.
            interval: return activations that (index + 1) % interval == 0, default interval = 1 (return all)
            
        Returns:
            Dictionary mapping layer names to activation tensors.
        """
        
        # Put activations that (index + 1) % interval == 0 into a new dictionary if interval is specified
        # if interval is not specified, return all activations

        activations = {}
        for key in list(self.activations.keys()):
            index = int(key.split('_')[-1])
            if (index + 1) % interval == 0:
                activations[key] = self.activations[key]  
        if clear:
            self.activations = {}
        return activations
    
    def extract_from_batch(
        self, 
        obs: torch.Tensor, 
        block_indices: Optional[List[int]] = None,
        interval: int = 1
    ) -> Dict[str, torch.Tensor]:
        """
        Convenience method to extract activations from a single forward pass.
        
        Args:
            obs: Input observation tensor
            block_indices: List of block indices to extract. If None, extracts all.
            interval: Return activations that (index + 1) % interval == 0, default interval = 1 (return all)
            
        Returns:
            Dictionary of activations
        """
        # Register hooks if not already done
        if not self.hooks:
            self.register_hooks(block_indices)
        
        # Clear previous activations
        self.activations = {}
        
        # Run forward pass
        with torch.no_grad():
            _ = self.model(obs)
        
        return self.get_activations(clear=False, interval=interval)
    
    def __enter__(self):
        """Context manager entry."""
        self.register_hooks()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up hooks."""
        self.remove_hooks()


def demo_extraction():
    """Demonstrate how to use the ActivationExtractor."""
    import torch
    from config import config
    
    print("=== Activation Extraction Demo ===\n")
    
    # Create model
    version = config['control']['version']
    conv_channels = config['resnet']['conv_channels']
    num_blocks = config['resnet']['num_blocks']
    
    print(f"Creating Brain model:")
    print(f"  Version: {version}")
    print(f"  Conv channels: {conv_channels}")
    print(f"  Num blocks: {num_blocks}\n")
    
    model = Brain(version=version, conv_channels=conv_channels, num_blocks=num_blocks)
    model.eval()
    
    # Create dummy input
    from libriichi.consts import obs_shape
    batch_size = 4
    obs = torch.randn(batch_size, *obs_shape(version))
    print(f"Input shape: {obs.shape}\n")
    
    # Method 1: Using context manager
    print("Method 1: Using context manager")
    with ActivationExtractor(model) as extractor:
        with torch.no_grad():
            output = model(obs)
        activations = extractor.get_activations()
    
    print(f"Extracted activations for {len(activations)} blocks")
    for name in sorted(activations.keys())[:3]:  # Show first 3
        print(f"  {name}: {activations[name].shape}")
    print(f"  ...\n")
    
    # Method 2: Manual hook management
    print("Method 2: Manual hook management (specific blocks)")
    extractor = ActivationExtractor(model)
    extractor.register_hooks(block_indices=[0, 10, 20, 39])  # Only specific blocks
    
    with torch.no_grad():
        output = model(obs)
    
    activations = extractor.get_activations()
    print(f"Extracted activations for {len(activations)} blocks")
    for name in sorted(activations.keys()):
        print(f"  {name}: {activations[name].shape}")
    
    extractor.remove_hooks()
    print()
    
    # Method 3: Using convenience method
    print("Method 3: Using convenience method")
    extractor = ActivationExtractor(model)
    activations = extractor.extract_from_batch(obs, block_indices=[0, 19, 39])
    
    print(f"Extracted activations for {len(activations)} blocks")
    for name in sorted(activations.keys()):
        shape = activations[name].shape
        mean_val = activations[name].mean().item()
        std_val = activations[name].std().item()
        print(f"  {name}: {shape}, mean={mean_val:.4f}, std={std_val:.4f}")
    
    extractor.remove_hooks()
    
    print("\n=== Demo Complete ===")


if __name__ == '__main__':
    demo_extraction()
