import docker

# Create a Docker client object using the local environment
client = docker.from_env()

def get_service_labels(service):
    """
    Retrieves the labels for a Docker service.

    Args:
        service (str): The name or ID of the Docker service.

    Returns:
        dict: A dictionary containing the labels for the service.

    Raises:
        docker.errors.NotFound: If the service with the specified name or ID is not found.
    """
    # Get the service object using the Docker client
    service = client.services.get(service)
    # Extract the labels from the service object
    return service.attrs['Spec']['Labels']

def can_autoscale(service):
    """
    Checks if a Docker service is allowed to be autoscaled.

    Args:
        service (str): The name or ID of the Docker service.

    Returns:
        bool: True if autoscaling is allowed for the service, False otherwise.

    Raises:
        docker.errors.NotFound: If the service with the specified name or ID is not found.
    """
    # Get the labels for the service
    labels = get_service_labels(service)
    # Check if the service has the "swarm.autoscaler" label set to "true"
    return labels.get('swarm.autoscaler') == 'true'

def scale_service(service, replicas):
    """
    Scales a Docker service to the specified number of replicas.

    Args:
        service (str): The name or ID of the Docker service.
        replicas (int): The number of replicas to scale the service to.

    Raises:
        docker.errors.NotFound: If the service with the specified name or ID is not found.
        docker.errors.APIError: If there is an error updating the service mode.
    """
    # Check if autoscaling is allowed for the service
    if can_autoscale(service):
        # Get the service object using the Docker client
        service = client.services.get(service)
        # Update the service to the specified number of replicas
        service.update(mode=service.mode.with_replicas(replicas))
        # Print a message indicating that the service was scaled
        print(f"Scaled {service.name} to {replicas} replicas")
    else:
        # Print a message indicating that autoscaling is not allowed for the service
        print(f"Autoscaling not allowed for {service.name}")
