import matplotlib.pyplot as plt

CUSTOM_PALETTE = {
        1: "#4285F4", # Google Core scheme
        2: "#34A853",
        3: "#FBBC04",
        4: "#EA4335",
        5: "#63BDFD", # Google Highlight scheme
        6: "#18D363",
        7: "#FFE000",
        8: "#FF8080",
        9: "#4285F4", # Google Core scheme
        10: "#34A853",
        11: "#FBBC04",
        12: "#EA4335",
        13: "#63BDFD", # Google Highlight scheme
        14: "#18D363",
        15: "#FFE000",
        16: "#FF8080",
    }

def generate_visual(df, user_id):
    img = plt.imread(f"/tmp/BG_{user_id}.jpg")
    fig, ax = plt.subplots(figsize=(19.20, 10.80))
    
    color_palette = [CUSTOM_PALETTE[shot_number] for shot_number in df['shot_number'].unique()]
    df['x'], df['y'] = 1080 - df['y'], df['x'] # For vertical visual

    shot_groups = df.groupby('shot_number')
    for i, (shot_number, data) in enumerate(shot_groups):
        ax.scatter(
            data['x'], 
            data['y'], 
            label=f"Shot {shot_number}", 
            color=color_palette[i], 
            s=15, 
            marker='o', 
            edgecolors='white', 
            linewidths=0.25
        )
    ax.legend()

    # plt.gca().invert_yaxis()
    # plt.gca().invert_xaxis()

    # Remove axis labels and ticks
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel('')
    ax.set_ylabel('')

    ax.imshow(img)
    plt.savefig('/tmp/trajectory.png')
    return
