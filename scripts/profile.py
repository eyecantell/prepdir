import cProfile
import pstats
from prepdir.main import run


def profile_run():
    cProfile.runctx('run(directory=".", quiet=True)', globals(), locals(), filename="prepdir_profile.prof")
    # Analyze results
    stats = pstats.Stats("prepdir_profile.prof")
    stats.sort_stats("cumulative").print_stats("prepdir", 20)  # Top 20 functions by cumulative time


if __name__ == "__main__":
    profile_run()
