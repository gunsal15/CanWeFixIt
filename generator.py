import torch
import torch.nn.functional as fun
from torch import nn

import params
from contextual_attention import ContextualAttention
from layers import GatedConv2D, GatedDeconv2D
from ops_util import resize_mask_like, normalize_tensor
from ops_visual import display_tensor_image


class Generator(nn.Module):
    def __init__(self):
        super(Generator, self).__init__()
        if params.device.type == "cuda":
            self.use_cuda = True
        else:
            self.use_cuda = False
        ch = params.ch_gen

        # stage_1
        self.conv1 = GatedConv2D(5, ch, kernel_size=5)
        self.conv2_downsample = GatedConv2D(ch, 2 * ch, stride=2)
        self.conv3 = GatedConv2D(2 * ch, 2 * ch)
        self.conv4_downsample = GatedConv2D(2 * ch, 4 * ch, stride=2)
        self.conv5 = GatedConv2D(4 * ch, 4 * ch)
        self.conv6 = GatedConv2D(4 * ch, 4 * ch)
        self.conv7_atrous = GatedConv2D(4 * ch, 4 * ch, dilation=2)
        self.conv8_atrous = GatedConv2D(4 * ch, 4 * ch, dilation=4)
        self.conv9_atrous = GatedConv2D(4 * ch, 4 * ch, dilation=8)
        self.conv10_atrous = GatedConv2D(4 * ch, 4 * ch, dilation=16)
        self.conv11 = GatedConv2D(4 * ch, 4 * ch)
        self.conv12 = GatedConv2D(4 * ch, 4 * ch)
        self.conv13_upsample = GatedDeconv2D(4 * ch, 2 * ch)
        self.conv14 = GatedConv2D(2 * ch, 2 * ch)
        self.conv15_upsample = GatedDeconv2D(2 * ch, ch)
        self.conv16 = GatedConv2D(ch, ch // 2)
        self.conv17 = GatedConv2D(ch // 2, 3, activation=None)

        # stage 2
        self.xconv1 = GatedConv2D(5, ch, kernel_size=5)
        self.xconv2_downsample = GatedConv2D(ch, ch, stride=2)
        self.xconv3 = GatedConv2D(ch, 2 * ch)
        self.xconv4_downsample = GatedConv2D(2 * ch, 2 * ch, stride=2)
        self.xconv5 = GatedConv2D(2 * ch, 4 * ch)
        self.xconv6 = GatedConv2D(4 * ch, 4 * ch)
        self.xconv7_atrous = GatedConv2D(4 * ch, 4 * ch, dilation=2)
        self.xconv8_atrous = GatedConv2D(4 * ch, 4 * ch, dilation=4)
        self.xconv9_atrous = GatedConv2D(4 * ch, 4 * ch, dilation=8)
        self.xconv10_atrous = GatedConv2D(4 * ch, 4 * ch, dilation=16)

        # attention branch
        self.pmconv1 = GatedConv2D(5, ch, kernel_size=5)
        self.pmconv2_downsample = GatedConv2D(ch, ch, stride=2)
        self.pmconv3 = GatedConv2D(ch, 2 * ch)
        self.pmconv4_downsample = GatedConv2D(2 * ch, 4 * ch, stride=2)
        self.pmconv5 = GatedConv2D(4 * ch, 4 * ch)
        self.pmconv6 = GatedConv2D(4 * ch, 4 * ch, activation=fun.relu)
        self.contextual_attention = ContextualAttention(4 * ch, 4 * ch)
        self.pmconv9 = GatedConv2D(4 * ch, 4 * ch)
        self.pmconv10 = GatedConv2D(4 * ch, 4 * ch)

        # concat xhalu and pm

        self.allconv11 = GatedConv2D(8 * ch, 4 * ch, 3, 1)
        self.allconv12 = GatedConv2D(4 * ch, 4 * ch, 3, 1)
        self.allconv13_upsample = GatedDeconv2D(4 * ch, 2 * ch)
        self.allconv14 = GatedConv2D(2 * ch, 2 * ch, 3, 1)
        self.allconv15_upsample = GatedDeconv2D(2 * ch, ch)
        self.allconv16 = GatedConv2D(ch, ch // 2)
        self.allconv17 = GatedConv2D(ch // 2, 3, activation=None)

    def forward(self, x, mask):
        # x: input image with erased parts
        # mask: binary tensor that shows erased parts

        # prepare input channels
        xin = x
        ones_x = torch.ones_like(x)[:, 0:1, :, :]
        x = torch.cat([x, ones_x, ones_x * mask], dim=1)

        # stage_1
        x = self.conv1(x)
        x = self.conv2_downsample(x)
        x = self.conv3(x)
        x = self.conv4_downsample(x)
        x = self.conv5(x)
        x = self.conv6(x)
        mask_s = resize_mask_like(mask, x)
        x = self.conv7_atrous(x)
        x = self.conv8_atrous(x)
        x = self.conv9_atrous(x)
        x = self.conv10_atrous(x)
        x = self.conv11(x)
        x = self.conv12(x)
        x = self.conv13_upsample(x)
        x = self.conv14(x)
        x = self.conv15_upsample(x)
        x = self.conv16(x)
        x = self.conv17(x)
        x = torch.tanh(x)
        x_stage_1 = x

        # prepare coarse result for stage 2
        # put generated patch into input image without patch
        x_inpaint = x_stage_1 * mask + xin[:, 0:3, :, :] * (1 - mask)
        x_inpaint.reshape(xin[:, 0:3, :, :].shape)
        x_inpaint = torch.cat([x_inpaint, ones_x, ones_x * mask], dim=1)

        # convolution branch
        x = self.xconv1(x_inpaint)
        x = self.xconv2_downsample(x)
        x = self.xconv3(x)
        x = self.xconv4_downsample(x)
        x = self.xconv5(x)
        x = self.xconv6(x)
        x = self.xconv7_atrous(x)
        x = self.xconv8_atrous(x)
        x = self.xconv9_atrous(x)
        x = self.xconv10_atrous(x)
        x_conv = x

        # attention branch
        x = self.pmconv1(x_inpaint)
        x = self.pmconv2_downsample(x)
        x = self.pmconv3(x)
        x = self.pmconv4_downsample(x)
        x = self.pmconv5(x)
        x = self.pmconv6(x)
        x, offset_flow = self.contextual_attention(x, x, mask_s)
        x = self.pmconv9(x)
        x = self.pmconv10(x)
        x_att = x

        # concatenate results from two branches and do the last convolutions
        x = torch.cat([x_conv, x_att], dim=1)
        x = self.allconv11(x)
        x = self.allconv12(x)
        x = self.allconv13_upsample(x)
        x = self.allconv14(x)
        x = self.allconv15_upsample(x)
        x = self.allconv16(x)
        x = self.allconv17(x)
        x = torch.tanh(x)
        x_stage_2 = x

        # return stage 1, stage 2 and offset flow results
        return x_stage_1, x_stage_2, offset_flow

    def inpaint_image(self, image, mask):
        # image: tensor with shape (im, im, 3), values (0-im)
        # mask: tensor with shape (im, im, 1), values (0-1)
        with torch.no_grad():
            image = image.permute(2, 0, 1)  # (3, im, im)
            mask = mask.permute(2, 0, 1)    # (1, im, im)
            image = image.unsqueeze(0).to(params.device)    # (1, 3, im, im)
            mask = mask.unsqueeze(0).to(params.device)      # (1, 1, im, im)
            image = normalize_tensor(image, (0, 255), (-1, 1))
            mask = normalize_tensor(mask, (0, 255), (0, 1))
            image_incomplete = image * (torch.tensor(1.) - mask)
            _, prediction, flow = self(image_incomplete, mask)
            image_complete = prediction * mask + image_incomplete * (1 - mask)
            image_complete = normalize_tensor(image_complete, (-1, 1), (0, 1))
            return image_complete
