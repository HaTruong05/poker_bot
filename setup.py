import os
from setuptools import find_packages, setup
from glob import glob

package_name = 'poker_bot'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'models'), glob('models/*.pt')),
        (os.path.join('share', package_name, 'models'), glob('models/*.xml')),  
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='matsuoke',
    maintainer_email='matsuoke@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'poker_bot = poker_bot.poker_bot:main',
        ],
    },
)
