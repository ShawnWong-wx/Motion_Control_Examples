
from ptychography import *
from optimizer import *


torch.set_default_tensor_type(torch.FloatTensor)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# %% ######################## System parameters ##########################
datapath = '../../data/'

# Multiple images
# data_name, wave_len, ps_sensor, z_os_init, img_num, shifts = "light_usaf_405nm_185um", 405e-9, 1.85e-6, torch.tensor(1120e-6), 25, [0, 0]

data_name, wave_len, ps_sensor, z_os_init, img_num, shifts = "light_usaf_405nm_110um/raw/", 405e-9, 1.1e-6, torch.tensor(
    1120e-6), 25, [0, 0]

# %% Parameters
mag = 4
img_size = 512

out_dir = "./output/"
data_dir = "../../data/"

img_size_up = mag * img_size
ps_up = ps_sensor / mag

data_dir = f'{data_dir}/{data_name}/'

# %%
holo_raw = load_data(data_dir=data_dir, file_type='tiff', img_num=img_num, img_size=img_size, shift=shifts)
holo_raw = torch.tensor(holo_raw).to(device)

# %% ######################## Position track ############################
pos_track = track_position(img_seq=holo_raw, is_mask=0)
pos_refine = pos_track
for iLoc in range(3):
    pos_refine = refine_position(img_seq=holo_raw, pos=pos_refine, is_mask=0)

fig, axes = plt.subplots(1, 3, figsize=(10, 3), sharey=False)
axes[0].imshow(holo_raw[:, :, 0].cpu()), axes[0].set_title('1st measurement')
axes[1].hist(holo_raw[:, :, 0].flatten().cpu(), bins=200, density=True), axes[1].set_title('Histogram')
axes[2].plot(pos_track[1, :], pos_track[0, :], 'bo-', markersize=3, alpha=0.5, label='track')
axes[2].plot(pos_refine[1, :], pos_refine[0, :], 'r.-', markersize=1, alpha=0.5, label='estimated')
axes[2].set_title('Scanning tracking'), axes[2].axis('equal'), axes[2].legend(loc='upper right', fontsize=8)
plt.show()
