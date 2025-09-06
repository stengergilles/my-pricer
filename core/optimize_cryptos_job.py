import logging
from core.optimizer import BayesianOptimizer
from core.parameter_manager import ParameterManager

logger = logging.getLogger(__name__)

def run_optimize_cryptos_job(n_trials: int = 30, top_count: int = 10, min_volatility: float = 5.0, max_workers: int = 3):
    """
    Optimizes parameters for volatile cryptocurrencies across all available strategies.
    """
    logger.info("Starting optimize cryptos job...")

    optimizer = BayesianOptimizer()
    param_manager = ParameterManager()
    available_strategies = param_manager.get_available_strategies()

    if not available_strategies:
        logger.warning("No strategies found for optimization.")
        return

    logger.info(f"Found {len(available_strategies)} strategies: {', '.join(available_strategies)}")

    for strategy_name in available_strategies:
        try:
            logger.info(f"Optimizing volatile cryptos for strategy: {strategy_name}")
            optimizer.optimize_volatile_cryptos(
                strategy=strategy_name,
                n_trials=n_trials,
                top_count=top_count,
                min_volatility=min_volatility,
                max_workers=max_workers
            )
            logger.info(f"Finished optimizing for strategy: {strategy_name}")
        except Exception as e:
            logger.error(f"Error optimizing for strategy {strategy_name}: {e}", exc_info=True)

    logger.info("Optimize cryptos job completed.")

if __name__ == "__main__":
    # Example usage when run directly
    logging.basicConfig(level=logging.INFO)
    run_optimize_cryptos_job()
