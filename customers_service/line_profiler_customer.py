from line_profiler import LineProfiler
from app import (
    register_customer,
    login_customer,
    get_current_user,
    get_all_customers,
    get_customer_by_username,
    update_customer,
    delete_customer,
    charge_wallet,
    deduct_wallet
)

def profile_functions():
    """
    Profile critical functions in customers_service.app and save results to a file.
    """
    profiler = LineProfiler()
    # Add unwrapped functions to the profiler
    profiler.add_function(register_customer.__wrapped__)
    profiler.add_function(login_customer.__wrapped__)
    profiler.add_function(get_current_user.__wrapped__)
    profiler.add_function(get_all_customers.__wrapped__)
    profiler.add_function(get_customer_by_username.__wrapped__)
    profiler.add_function(update_customer.__wrapped__)
    profiler.add_function(delete_customer.__wrapped__)
    profiler.add_function(charge_wallet.__wrapped__)
    profiler.add_function(deduct_wallet.__wrapped__)

    # Execute the main function or simulate API calls here
    profiler.enable_by_count()
    try:
        # Simulate API call or test the function
        register_customer.__wrapped__()  # Call unwrapped function
    except Exception as e:
        print(f"Error during profiling: {e}")
    finally:
        with open("line_profiler_output.txt", "w") as f:
            profiler.print_stats(stream=f)  # Save output to file
        print("Profiling results saved to line_profiler_output.txt")

if __name__ == "__main__":
    profile_functions()
