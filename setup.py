#!/usr/bin/env python3

from glob import glob

from setuptools import find_packages, setup

package_name = 'cleanbit_simulate'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(include=[package_name, f'{package_name}.*']),
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/data', glob('data/*.csv')),
        (f'share/{package_name}/models', glob('models/*')),
    ],
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
            'nlu_node = cleanbit_simulate.nlu.nlu_node:main'
        ],
    },
)
