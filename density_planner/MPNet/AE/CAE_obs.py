import argparse
import os
import torch
from torch import nn
from mpnet_data.simulation_objects import StaticObstacle, Environment, DynamicObstacle
import numpy as np
import hyperparams
from torch.utils.data import TensorDataset
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
from mpnet_data.plot import plot

# https://medium.com/dataseries/convolutional-autoencoder-in-pytorch-on-mnist-dataset-d65145c132ac

class Encoder(nn.Module):
    def __init__(self):
        super(Encoder, self).__init__()
        # convolutional layer
        self.encoder = nn.Sequential(
            # convolutional layer
            nn.MaxPool2d(kernel_size=2, stride=2),
            nn.Conv2d(1, 8, 5, stride=2, padding=1),
            nn.PReLU(),
            nn.Conv2d(8, 16, 5, stride=2, padding=1),
            nn.BatchNorm2d(16),
            nn.PReLU(),
            nn.Conv2d(16, 32, 5, stride=2, padding=0),
            nn.PReLU(),

            nn.Flatten(start_dim=1),

            # linear layer
            nn.Linear(32 * 13 * 23, 2048), nn.PReLU(), nn.Linear(2048, 512), nn.PReLU(), nn.Linear(512, 128),
            nn.PReLU(), nn.Linear(128, 28)
        )

    # #convolutional layer #1*240*400
    # self.conv = self.encoder_cnn = nn.Sequential(
    # 	#1*240*400
    # 	nn.MaxPool2d(kernel_size=2, stride=2),
    #     nn.Conv2d(1, 8, 5, stride=2, padding=1),
    #     nn.PReLU(),
    #     nn.Conv2d(8, 16, 5, stride=2, padding=1),
    #     nn.PReLU(),
    # 	nn.Conv2d(16, 32, 5, stride=2, padding=0),
    #     nn.PReLU(),
    # )
    #
    # #flatten
    # self.flatten = nn.Flatten(start_dim=0)
    #
    # #linear
    # self.lin = nn.Sequential(nn.Linear(32*13*23, 2048),nn.PReLU(),nn.Linear(2048, 512),nn.PReLU(),nn.Linear(512, 128),nn.PReLU(),nn.Linear(128, 28))

    def forward(self, x):
        x = self.encoder(x)
        # x = self.conv(x)
        # x = self.flatten(x)
        # x = self.lin(x)
        return x


class Decoder(nn.Module):
    def __init__(self):
        super(Decoder, self).__init__()

        self.decoder = nn.Sequential(
            # linear layer
            nn.Linear(28, 128), nn.PReLU(), nn.Linear(128, 512), nn.PReLU(), nn.Linear(512, 2048), nn.PReLU(),
            nn.Linear(2048, 32 * 13 * 23),

            # flatten
            nn.Unflatten(dim=1, unflattened_size=(32, 13, 23)),

            # de-convolutional layer
            nn.ConvTranspose2d(32, 16, 5,
                               stride=2, output_padding=0),
            nn.BatchNorm2d(16),
            nn.PReLU(),
            nn.ConvTranspose2d(16, 8, 5, stride=2,
                               padding=1, output_padding=1),
            nn.PReLU(),
            nn.ConvTranspose2d(8, 1, 5, stride=2,
                               padding=1, output_padding=0),
            nn.PReLU(),
            nn.Upsample(size=(241, 401))
        )

    # self.lin = nn.Sequential(nn.Linear(28, 128),nn.PReLU(),nn.Linear(128, 512),nn.PReLU(),nn.Linear(512, 2048),nn.PReLU(),nn.Linear(2048, 32*13*23))
    #
    # self.unflatten = nn.Unflatten(dim=0,unflattened_size=(32, 13, 23))
    #
    # self.deconv = nn.Sequential(
    # 	nn.ConvTranspose2d(32, 16, 5,
    # 					  stride=2, output_padding=0),
    # 	nn.PReLU(),
    # 	nn.ConvTranspose2d(16, 8, 5, stride=2,
    # 					   padding=1, output_padding=1),
    # 	nn.PReLU(),
    # 	nn.ConvTranspose2d(8, 1, 5, stride=2,
    # 					   padding=1, output_padding=0),
    # 	nn.PReLU(),
    # 	nn.Upsample(size=(241,401))
    # )

    def forward(self, x):
        x = self.decoder(x)
        # x = self.lin(x)
        # x = self.unflatten(x)
        # x = self.deconv(x)
        return x


mse_loss = nn.MSELoss()
lam = 1e-3


def loss_function(W, x, recons_x, h):
    mse = mse_loss(recons_x, x)
    """
	W is shape of N_hidden x N. So, we do not need to transpose it as opposed to http://wiseodd.github.io/techblog/2016/12/05/contractive-autoencoder/
	"""
    dh = h * (1 - h)  # N_batch x N_hidden
    contractive_loss = torch.sum(W ** 2, dim=1).sum().mul_(lam)
    return mse + contractive_loss


def load_env(i):
    ### load hyperparameters
    args = hyperparams.parse_args()

    directory = "./mpnet_data/env/" + str(i)

    env_file = ""
    start_goal_file = ""

    files = os.listdir(directory)

    for file in files:
        if file[-3:] == "npy":
            if file.find("env_" + str(i) + ".npy") != -1:
                env_file = file

    obslist = np.load(directory + "/" + env_file, allow_pickle=True)

    objects = []
    for i in range(len(obslist)):
        obs, gps_dynamics = obslist[i]
        map = DynamicObstacle(args, name="gpsmaps%d" % i, coord=obs, velocity_x=gps_dynamics[1],
                              velocity_y=gps_dynamics[2],
                              gps_growthrate=gps_dynamics[0], isgps=True)
        objects.append(map)

    environment = Environment(objects, args)

    # return environment.grid.numpy()
    return environment.grid


def main(args):
    seed = 10
    torch.manual_seed(seed)

    encoder = Encoder()
    decoder = Decoder()

    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda"
        encoder.to(device)
        decoder.to(device)

    params = list(encoder.parameters()) + list(decoder.parameters())
    optimizer = torch.optim.Adam(params)
    avg_loss_list = []

    if not os.path.exists(args.model_path):
        os.makedirs(args.model_path)

    env_list = torch.ones((args.total_env_num - 100, 1, 241, 401)).to(device)

    print("load env ")
    for env_num in range(args.total_env_num - 100):
        # load environment
        env_grid = load_env(env_num).permute(2, 0, 1).unsqueeze(dim=0).to(device)
        env_list[env_num] = env_grid

    dataset = TensorDataset(env_list)
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    print("env loaded")

    print("training starts")
    ctr = 0
    for epoch in range(args.num_epochs):
        print("epoch" + str(epoch))
        avg_loss = 0

        for batch_idx, batch in enumerate(dataloader):
            optimizer.zero_grad()
            decoder.zero_grad()
            encoder.zero_grad()
            cur_grid_batch = batch[0].to(device)

            # ===================forward=====================
            latent_space = encoder(cur_grid_batch)
            output = decoder(latent_space)
            keys = encoder.state_dict().keys()
            W = encoder.state_dict()[
                'encoder.15.weight']  # regularize or contracting last layer of encoder. Print keys to displace the layers name.
            loss = loss_function(W, cur_grid_batch, output, latent_space)
            avg_loss = avg_loss + loss.data
            # ===================backward====================
            loss.backward()
            optimizer.step()

        if ctr == 0:
            ctr = 1

        print("--average loss:")
        avg_loss = avg_loss.cpu().numpy() / args.batch_size / ctr
        print(avg_loss)
        avg_loss_list.append(avg_loss)

    print("validation starts")
    env_list = torch.zeros((args.total_env_num - 100, 1, 1, 241, 401)).to(device)

    idx = 0
    for env_num in range(args.total_env_num - 100, args.total_env_num):
        # load environment
        print("load env " + str(env_num))
        env_grid = load_env(env_num).permute(2, 0, 1).unsqueeze(dim=0).to(device)
        env_list[idx] = env_grid
        idx += 1
    print("Env loaded")

    avg_loss = 0
    start_val_env = args.total_env_num - 100
    for i in range(start_val_env, args.total_env_num):
        optimizer.zero_grad()
        decoder.zero_grad()
        encoder.zero_grad()

        # ===================forward=====================
        cur_grid_batch = env_list[i - start_val_env]
        print(cur_grid_batch.shape)
        latent_space = encoder(cur_grid_batch)
        output = decoder(latent_space)
        keys = encoder.state_dict().keys()
        W = encoder.state_dict()[
            'encoder.15.weight']  # regularize or contracting last layer of encoder. Print keys to displace the layers name.
        loss = loss_function(W, cur_grid_batch, output, latent_space)
        avg_loss = avg_loss + loss.data

    print("--Validation average loss:")
    avg_loss = avg_loss.cpu().numpy() / 100
    print(avg_loss)

    avg_loss_list = np.array(avg_loss_list)
    val_loss = np.array(avg_loss)

    torch.save(encoder.state_dict(), os.path.join(args.model_path, 'cae_obs_encoder.model'))
    torch.save(decoder.state_dict(), os.path.join(args.model_path, 'cae_obs_decoder.model'))
    np.save(os.path.join(args.model_path, 'obs_avg_loss_list.npy'), avg_loss_list)
    np.save(os.path.join(args.model_path, 'obs_val_loss.npy'), val_loss)
    
    plot(args.model_path)

def encode_obs(args):
    seed = args.seed
    torch.manual_seed(seed)

    encoder = Encoder()

    device = "cpu"
        
    model = torch.load(os.path.join(args.model_path,'cae_obs_encoder.model'), map_location=torch.device('cpu'))
    encoder.load_state_dict(model)

    env_list = torch.ones((args.total_env_num, 1, 241, 401)).to(device)

    print("load env ")
    for env_num in range(args.total_env_num):
        # load environment
        env_grid = load_env(env_num).permute(2, 0, 1).unsqueeze(dim=0).to(device)
        env_list[env_num] = env_grid

    dataset = TensorDataset(env_list)
    dataloader = DataLoader(dataset, batch_size=args.total_env_num, shuffle=False)
    print("env loaded")

    latent_space_list = []

    for batch_idx, batch in enumerate(dataloader):
        cur_grid_batch = batch[0].to(device)

        # ===================forward=====================
        latent_space = encoder(cur_grid_batch)
        latent_space_list.append(latent_space)

    latent_space_list = torch.cat(latent_space_list, dim = 0).to("cpu")

    return latent_space_list

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # mpnet training data generation
    parser.add_argument('--gps_training_data_generation', type=bool, default=True)
    parser.add_argument('--gps_training_env_path', type=str, default="mpnet_data/env/")
    parser.add_argument('--total_env_num', type=int, default=500)
    parser.add_argument('--training_env_num', type=int, default=500)
    parser.add_argument('--training_traj_num', type=int, default=10)
    parser.add_argument('--model_path', type=str, default='./mpnet_data/models/', help='path for saving trained models')
    parser.add_argument('--data_path', type=str, default='./mpnet_data/', help='path for saving data')
    parser.add_argument('--num_epochs', type=int, default=800)
    parser.add_argument('--batch_size', type=int, default=100)
    parser.add_argument('--learning_rate', type=float, default=0.001)
    args = parser.parse_args()
    main(args)
