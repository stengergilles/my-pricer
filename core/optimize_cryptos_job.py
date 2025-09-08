import logging
import os
from core.optimizer import BayesianOptimizer
from core.parameter_manager import ParameterManager
from core.app_config import Config
from . import job_status_manager # Import job_status_manager
from core.logger_config import setup_job_logging # Import the new logging setup function

def run_optimize_cryptos_job(
    *, # Mark subsequent arguments as keyword-only
    job_id: str,
    n_trials: int = 30,
    top_count: int = 10,
    min_volatility: float = 5.0,
    max_workers: int = 3,
    strategy_config: dict = None  # New parameter for strategy-specific configurations
):
    """
    Optimizes parameters for volatile cryptocurrencies across all available strategies.
    Optionally accepts strategy_config to provide specific parameters for each strategy.
    """
    log_path = setup_job_logging(job_id)
    logger = logging.getLogger(job_id)

    logger.info("Starting optimize cryptos job...")
    job_status_manager.update_job_status(job_id, 'running', 'Optimization started.', log_path=log_path) # Update status
    logger.debug(f"Job {job_id} status set to 'running'.") # Added debug log

    config = Config()
    optimizer = BayesianOptimizer(results_dir=config.RESULTS_DIR, logger=logger)
    param_manager = ParameterManager()
    available_strategies = param_manager.get_available_strategies()

    if not available_strategies:
        error_message = "No strategies found for optimization."
        logger.warning(error_message)
        job_status_manager.update_job_status(job_id, 'failed', error_message) # Update status on error
        return

    logger.info(f"Found {len(available_strategies)} strategies: {', '.join(available_strategies)}")

    for strategy_name in available_strategies:
        if job_status_manager.is_job_stop_requested(job_id):
            logger.info(f"Job {job_id} stop requested. Exiting optimization for remaining strategies.")
            job_status_manager.update_job_status(job_id, 'stopped', 'Optimization stopped by user.')
            return
        try:
            logger.info(f"Optimizing volatile cryptos for strategy: {strategy_name}")
            job_status_manager.update_job_status(job_id, 'running', f'Optimizing strategy: {strategy_name}') # Update status for current strategy
            
            # Get strategy-specific parameters if provided
            current_strategy_params = strategy_config.get(strategy_name, {}) if strategy_config else {}

            optimizer.optimize_volatile_cryptos(
                strategy=strategy_name,
                n_trials=n_trials,
                top_count=top_count,
                min_volatility=min_volatility,
                max_workers=max_workers,
                job_id=job_id, # Added job_id
                **current_strategy_params  # Unpack strategy-specific parameters
            )
            
            # Check again after each strategy completes
            if job_status_manager.is_job_stop_requested(job_id):
                logger.info(f"Job {job_id} stop requested after completing strategy {strategy_name}.")
                job_status_manager.update_job_status(job_id, 'stopped', 'Optimization stopped by user.')
                return
                
            logger.info(f"Finished optimizing for strategy: {strategy_name}")
        except Exception as e:
            error_message = f"Error optimizing for strategy {strategy_name}: {e}"
            logger.error(error_message, exc_info=True)
            job_status_manager.update_job_status(job_id, 'failed', error_message) # Update status on error
            # Continue to next strategy even if one fails

    # The status is now updated by optimizer.optimize_volatile_cryptos
    logger.info("Optimize cryptos job completed.")

if __name__ == "__main__":
    # Example usage when run directly
    logging.basicConfig(level=logging.INFO)
    run_optimize_cryptos_job()
