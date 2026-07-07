"""
demo_connector.py
==================
End-to-end demo: GAE + Shape Board connector.

Runs the pipeline on:
1. Chemical Plant
2. Global Food System
"""

from gae_shape_connector import create_and_visualize_system
from shape_board import main as shape_board_main

# Chemical Plant System
chemical_nodes = ["Sun", "Fresnel_Lens", "Pyrite", "Qanat", "Clay", "Apprentices", "Acid", "Brine", "Sage"]
chemical_edges = [
    ("Sun", "Fresnel_Lens"),
    ("Fresnel_Lens", "Pyrite"),
    ("Pyrite", "Acid"),
    ("Qanat", "Brine"),
    ("Brine", "Sage"),
    ("Apprentices", "Fresnel_Lens"),
    ("Apprentices", "Qanat"),
    ("Apprentices", "Clay"),
    ("Clay", "Acid"),
]
chemical_descriptions = {
    "Sun": "Primary energy source",
    "Fresnel_Lens": "Concentrates sunlight for heat",
    "Pyrite": "Source of sulfur for acid production",
    "Qanat": "Passive water cooling and brine supply",
    "Clay": "Material for reactor linings and ceramics",
    "Apprentices": "Human knowledge and skill",
    "Acid": "Sulfuric acid output",
    "Brine": "Saltwater for evaporation and lens cleaning",
    "Sage": "Olfactory anchor for knowledge retention"
}

# Global Food System
food_nodes = ["Cropland", "Freshwater", "Fertilizer", "Fossil_Fuel", "Global_Trade", "Seed_Stock"]
food_edges = [
    ("Fossil_Fuel", "Fertilizer"),
    ("Fertilizer", "Cropland"),
    ("Freshwater", "Cropland"),
    ("Cropland", "Global_Trade"),
    ("Global_Trade", "Seed_Stock"),
    ("Seed_Stock", "Cropland"),
]
food_descriptions = {
    "Cropland": "Agricultural land",
    "Freshwater": "Irrigation water",
    "Fertilizer": "Synthetic NPK fertilizer",
    "Fossil_Fuel": "Energy for tractors and shipping",
    "Global_Trade": "International food distribution",
    "Seed_Stock": "Commercial hybrid seeds"
}

if __name__ == "__main__":
    print("\n" + "="*80)
    print("GAE + SHAPE BOARD CONNECTOR DEMO")
    print("="*80)
    
    # Demo 1: Chemical Plant
    board_chemical, results_chemical = create_and_visualize_system(
        "Chemical Plant",
        chemical_nodes,
        chemical_edges,
        chemical_descriptions
    )
    
    # Show the 3D visualization for Chemical Plant
    fig_chemical = board_chemical.visualize()
    fig_chemical.show()
    
    # Demo 2: Global Food System
    board_food, results_food = create_and_visualize_system(
        "Global Food System",
        food_nodes,
        food_edges,
        food_descriptions
    )
    
    # Show the 3D visualization for Global Food System
    fig_food = board_food.visualize()
    fig_food.show()
    
    print("\n" + "="*80)
    print("DEMO COMPLETE")
    print("="*80)
    print("\nThe Shape Board now visualizes the recommended geometry for each system.")
    print("Nodes are mapped to the system's actual tasks.")
    print("The Shape Guardian monitors integrity and suggests actions.")
