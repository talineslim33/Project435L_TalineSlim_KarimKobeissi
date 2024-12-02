from line_profiler import LineProfiler
from app import (
    submit_review,
    update_review,
    delete_review,
    flag_review,
    moderate_review,
    get_product_reviews,
    get_customer_reviews,
    get_flagged_reviews,
    get_review_details,
)

def profile_functions():
    profiler = LineProfiler()

    # Add the original, unwrapped functions
    profiler.add_function(submit_review.__wrapped__)
    profiler.add_function(update_review.__wrapped__)
    profiler.add_function(delete_review.__wrapped__)
    profiler.add_function(flag_review.__wrapped__)
    profiler.add_function(moderate_review.__wrapped__)
    profiler.add_function(get_product_reviews)
    profiler.add_function(get_customer_reviews.__wrapped__)
    profiler.add_function(get_flagged_reviews.__wrapped__)
    profiler.add_function(get_review_details.__wrapped__)

    profiler.enable_by_count()

    profiler.disable()

    # Save results to a file
    with open(r"C:\Users\User\Desktop\line_profiler_results.txt", "w") as file:
        profiler.print_stats(stream=file)


    print("Profiling results saved to line_profiler_results.txt")


if __name__ == "__main__":
    profile_functions()
