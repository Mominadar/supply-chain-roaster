import os


def save_dataframes(dataframes, target, save_path):
    """
    Save pandas DataFrames to CSV files.

    Args:
        dataframes (dict): Dictionary mapping dataset names to DataFrames
        target (str): Target dataset name to save, or 'all' to save all
        save_path (str): Path to save the CSV files
    """
    os.makedirs(save_path, exist_ok=True)

    if target == "all":
        for name, df in dataframes.items():
            df.to_csv(os.path.join(save_path, f"{name}.csv"), index=False)
    elif target in dataframes:
        dataframes[target].to_csv(os.path.join(save_path, f"{target}.csv"), index=False)
    else:
        raise ValueError(f"Unknown target: {target}")
