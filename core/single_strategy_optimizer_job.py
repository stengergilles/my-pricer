import logging
from core.optimizer import BayesianOptimizer
from core.parameter_manager import ParameterManager
from core.app_config import Config # Assuming Config is needed for optimizer
from . import job_status_manager # Import job_status_manager
from core.logger_config import setup_job_logging # Import the new logging setup function

def run_single_strategy_optimization_job(
    *, # Mark subsequent arguments as keyword-only
    job_id: str,
    strategy_name: str,
    n_trials: int = 30,
    top_count: int = 10,
    min_volatility: float = 5.0,
    max_workers: int = 3
):
    """
    Optimizes a single strategy across discovered volatile cryptocurrencies.
    Mirrors the functionality of volatile_crypto_optimizer_v2.py.
    """
    log_path = setup_job_logging(job_id)
    logger = logging.getLogger(job_id)

    logger.info(f"Starting single strategy optimization job for strategy: {strategy_name}")
    job_status_manager.update_job_status(job_id, 'running', 'Optimization started.', log_path=log_path) # Update status

    optimizer = BayesianOptimizer(logger=logger)
    param_manager = ParameterManager()

    if strategy_name not in param_manager.get_available_strategies():
        error_message = f"Strategy '{strategy_name}' not found among available strategies."
        logger.error(error_message)
        job_status_manager.update_job_status(job_id, 'failed', error_message) # Update status on error
        return

    try:
        # The optimize_volatile_cryptos method in BayesianOptimizer
        # is expected to handle the discovery of volatile cryptos internally
        # and apply the optimization for the given strategy.
        optimizer.optimize_volatile_cryptos(
            strategy=strategy_name,
            n_trials=n_trials,
            top_count=top_count,
            min_volatility=min_volatility,
            max_workers=max_workers
        )
        logger.info(f"Finished single strategy optimization for strategy: {strategy_name}")
        job_status_manager.update_job_status(job_id, 'completed', 'Optimization completed successfully.') # Update status on success
    except Exception as e:
        error_message = f"Error optimizing single strategy {strategy_name}: {e}"
        logger.error(error_message, exc_info=True)
        job_status_manager.update_job_status(job_id, 'failed', error_message)

    logger.info("Single strategy optimization job completed.")

if __name__ == "__main__":
    # Example usage when run directly
    logging.basicConfig(level=logging.INFO)
    # Example: Optimize 'EMA_Only' strategy
    run_single_strategy_optimization_job(
        strategy_name="EMA_Only",
        n_trials=50
    )
