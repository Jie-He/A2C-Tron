# A2C-Tron
Jie, Naomi, Max

## Standard Libraries
Copy, Numpy, Time, Matplotlib, OS, datetime, collections, random

## Special libaries
Pytorch, OpenCV (For GUI), 

## Model weights
We provided the pretrained models weights in the models/ folder.
    + A2C_2 (Trained with bot depth 2) - 540K episodes trained
    + A2C_5 (Trained with bot depth 5) - 470K episodes trained
    + DQN_5 (Trained with bot depth 5) - 100K episodes trained

## Example training commands:
  ++ CUDA_VISIBLE_DEVICES=ID only when you want to use specific GPU
  ++ Listed commandlines are used on the ogg.cs.bath.ac.uk GPU server
  ++ CUDA_VISIBLE_DEVICES is only avaliable on Nvidia graphics card equipt hardware

  ## Train A2C with bot of depth 2 and save models in folder "A2C_2"
    CUDA_VISIBLE_DEVICES=5 python main.py --epochs=500000 --model_name=A2C_2 --depth=2 --savefreq=50000

  ## Train A2C with bot of depth 5 and save models in folder "A2C_5"
    CUDA_VISIBLE_DEVICES=5 python main.py --epochs=500000 --model_name=A2C_5 --depth=5 --savefreq=50000

  ## Train DQN with bot of depth 5 and save models in folder "DQN_5"
  ## Note, need --model_type=DQN flag (Default is A2C)
    CUDA_VISIBLE_DEVICES=5 python main.py --epochs=500010 --model_type=DQN --model_name=DQN_5 --depth=5 --savefreq=25000

## Running with commandline flags (With GUI):
python main.py --epochs=100 --model_name=A2C_2 --gui=1 --depth=2
    + Plays 100 games
    + Loads the latest model from folder A2C_2

## For more information of the commandline flags, see the options.py file.
