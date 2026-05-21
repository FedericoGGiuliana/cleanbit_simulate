#!/usr/bin/env python3

from setuptools import setup

package_name = 'cleanbit_simulate'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    install_requires=['setuptools','pyserial'],
    zip_safe=True,
    maintainer='simenza',
    maintainer_email='simenza@example.com',
    description='Differential drive robot with Gazebo and ROS 2',
    license='MIT',
    entry_points={
        'console_scripts': [
            'odom_to_tf = cleanbit_simulate.odom_to_tf:main',
            'supervisor = cleanbit_simulate.supervisor:main',
            'map_manager = cleanbit_simulate.map_manager_node:main',

            'cleaning_controller = cleanbit_simulate.cleaning_controller:main'
        ],
    },
)
