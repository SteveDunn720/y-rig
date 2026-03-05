import logging

log = logging.getLogger(__name__)


def reload_components() -> None:
    """Reload all mGear shifter components.

    This picks up changes to any component on
    ``MGEAR_SHIFTER_COMPONENT_PATH``, including the y-rig custom
    components (``y_arm_01``, ``y_leg_01``, ``y_spine_01``, etc.).
    """
    from mgear.shifter import reloadComponents

    reloadComponents()
    log.info("Reloaded mGear shifter components")
