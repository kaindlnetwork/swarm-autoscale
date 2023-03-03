"""
This module provides functions for managing Docker services.
"""

import logging

try:
    import docker
except ImportError as e:
    logging.error("Failed to import docker library: %s", e)

# Create a Docker client object using the local environment
client = docker.from_env()

# Create a logger object
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a file handler and set its log level to INFO
file_handler = logging.FileHandler('autoscaler.log')
file_handler.setLevel(logging.INFO)

# Create a formatter and set it as the file handler's formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

def get_service_labels(service):
    """
    Retrieves the labels for a Docker service.
    Args:
        service (str): The name or ID of the Docker service.
    Returns:
        dict: A dictionary containing the labels for the service.
    Raises:
        ValueError: If the service name is not provided.
        docker.errors.NotFound: If the service with the specified name or ID is not found.
    """
    if not service:
        raise ValueError("Service name not provided")
    try:
        # Get the service object using the Docker client
        service = client.services.get(service)
        # Extract the labels from the service object
        return service.attrs['Spec']['Labels']
    except docker.errors.NotFound as ex:
        logger.error("Error: Service not found - %s", ex)
        raise

def can_autoscale(service):
    """
    Checks if a Docker service is allowed to be autoscaled.
    Autoscaling is allowed only if:
    - The service has the "swarm.autoscaler" label set to "true".
    - The integer value of the "swarm.autoscaler.maximum" label (if it exists)
      is greater than the current number of replicas.

    Args:
        service (str): The name or ID of the Docker service.

    Returns:
        bool: True if autoscaling is allowed for the service, False otherwise.

    Raises:
        ValueError: If the service name is not provided.
        docker.errors.NotFound: If the service with the specified name or ID is not found.
    """
    if not service:
        raise ValueError("Service name not provided")

    try:
        # Get the labels for the service
        labels = get_service_labels(service)
        # Check if the service has the "swarm.autoscaler" label set to "true"
        autoscale_enabled = labels.get('swarm.autoscaler') == 'true'

        if autoscale_enabled:
            # Check if the service has a "swarm.autoscaler.maximum" label
            max_replicas_label = labels.get('swarm.autoscaler.maximum')
            if max_replicas_label is not None:
                try:
                    # Attempt to parse the label value as an integer
                    max_replicas = int(max_replicas_label)
                    # Check if the current number of replicas is less than the maximum
                    current_replicas = get_service_replicas(service)
                    return current_replicas < max_replicas
                except ValueError:
                    # If the label value is not a valid integer, log an error and disable autoscaling
                    logger.error(f"Error: Invalid value for 'swarm.autoscaler.maximum' label: {max_replicas_label}")
                    return False
            else:
                # If the "swarm.autoscaler.maximum" label does not exist, autoscaling is allowed
                return True
        else:
            # If the "swarm.autoscaler" label is not set to "true", autoscaling is not allowed
            return False

    except docker.errors.NotFound as error:
        logger.error(f"Error: Service not found - {error}")
        raise


def scale_service(service, replicas):
    """
    Scales a Docker service to the specified number of replicas.
    Args:
        service (str): The name or ID of the Docker service.
        replicas (int): The number of replicas to scale the service to.
    Raises:
        ValueError: If the service name or number of replicas is not provided.
        docker.errors.NotFound: If the service with the specified name or ID is not found.
        docker.errors.APIError: If there is an error updating the service mode.
    """
    if not service:
        raise ValueError("Service name not provided")
    if not replicas:
        raise ValueError("Number of replicas not provided")
    try:
        # Check if autoscaling is allowed for the service
        if can_autoscale(service):
            # Get the service object using the Docker client
            service_obj = client.services.get(service)
            # Update the service to the specified number of replicas
            service_obj.update(mode=service_obj.mode.with_replicas(replicas))
            # Log a message indicating that the service was scaled
            logger.info("Scaled %s to %d replicas", service_obj.name, replicas)
        else:
            # Log a message indicating that autoscaling is not allowed for the service
            logger.warning("Autoscaling not allowed for %s", service)
    except docker.errors.NotFound as ex:
        logger.error("Error: Service not found - %s", ex)
        raise
    except docker.errors.APIError as ex:
        logger.error("Error: Failed to update service - %s", ex)
        raise
    except ValueError as ex:
        logger.error("Error: Invalid input - %s", ex)
        raise
