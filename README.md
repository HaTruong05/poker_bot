**PokerBot** is a Texas Hold'em poker dealer. Pokerbot scans the players, reads their hands, reads the community cards, calculates the winning hand, and physically turns to congratulate the winner.


## What you need

* ROS 2 jazzy
* TurtleBot3
* Python 3 Dependencies:
  * `opencv-python`
  * `cv-bridge`
  * `numpy`
  * `ultralytics`

## What to download

1. Clone the whole repository in src in your ros2_ws

2. Copy face model (`haarcascade_frontalface_default.xml`) and card model (`poker_best.pt`) and into `ros2_ws/install/poker_bot/share/poker_bot/models`
3. Install ROS dependencies and build the package:
```bash
cd ~/ros2_ws
colcon build --packages-select poker_bot

```


4. Source your workspace:
```bash
source install/setup.bash

```
5. run the node:
```bash
ros2 run poker_bot poker_bot
```


## How to play
1. You need players (2+ people, but one person can play multiple players too)
2. Playing cards (no jokers)
3. Run the code, and turtlebot should start spinning in place
4. Show player 1's face to the camera
5. When turtlebot stops spinning, show player 1's hands to the camera one by one
6. Repeat until it sees all players (you must not move around)
7. When it stops spinning, show the community cards to the camera one by one
8. Then the turtlebot should turn to the winner and cheer


## File Structure

* `poker_bot.py`: The main ROS 2 node managing state, movement, and computer vision.
* `poker.py`: A pure Python Texas Hold'em game and hand evaluation engine.
* `package.xml` & `setup.py`: ROS 2 Python package configuration files.
* `models/`: Directory holding the `.pt` YOLO weights and `.xml` Haar cascades.
"""
