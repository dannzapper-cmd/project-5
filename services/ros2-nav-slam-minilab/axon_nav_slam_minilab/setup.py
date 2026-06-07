import os
from glob import glob

from setuptools import find_packages, setup

package_name = "axon_nav_slam_minilab"

setup(
    name=package_name,
    version="0.5.5",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
        (os.path.join("share", package_name, "maps"), glob("maps/*")),
    ],
    install_requires=["setuptools", "requests"],
    zip_safe=True,
    maintainer="AXON Contributors",
    maintainer_email="axon@example.com",
    description="AXON Phase 5.5 headless ROS2 Nav2 + SLAM MiniLab (simulated rehab lab)",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "mini_world_node = axon_nav_slam_minilab.mini_world_node:main",
            "nav_goal_runner = axon_nav_slam_minilab.nav_goal_runner:main",
            "slam_status_node = axon_nav_slam_minilab.slam_status_node:main",
            "axon_nav_slam_bridge = axon_nav_slam_minilab.axon_nav_slam_bridge:main",
        ],
    },
)
