import os
import logging

logging.basicConfig(level=logging.INFO)


def run(style, image):
    logging.warning("Starting CycleGAN processing...")
    os.system(f"python models/GAN/test.py --dataroot images/ --checkpoints_dir models/GAN/weights "
              f"--name {style}_pretrained --model test --no_dropout")
    logging.warning("GAN style transfer finished!")
    os.remove(f"images/{image}.jpg")
