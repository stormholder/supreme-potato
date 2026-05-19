STAGES = [
    "style_enforcer",
    "prompt_writer",
    "generate_images",
    "critic",
    "refine_prompts",
    "generate_3d",
    "blender_cleanup",
]

REQUIRES = {
    "prompt_writer": [
        "refined_brief",
    ],

    "generate_images": [
        "prompts",
    ],

    "critic": [
        "images",
    ],

    "refine_prompts": [
        "critique",
    ],

    "generate_3d": [
        "images",
    ],

    "blender_cleanup": [
        "mesh_path",
    ],
}