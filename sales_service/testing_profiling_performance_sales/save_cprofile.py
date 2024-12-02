import pstats

# Load the profile data
with open("cprofile_output.txt", "w") as f:
    stats = pstats.Stats("output.prof", stream=f)
    stats.strip_dirs()  # Remove long directory paths for better readability
    stats.sort_stats("time")  # Sort by time (can also use "cumulative", "calls", etc.)
    stats.print_stats()  # Print stats to the file
