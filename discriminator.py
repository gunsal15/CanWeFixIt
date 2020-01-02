from layers import *

class Discriminator(nn.Module):
    def __init__(self):
        super(Discriminator, self).__init__()
        cnum = 64
        inp = 256
        self.conv1 = SpectralConv2D(inp, 3, cnum)
        self.conv2 = SpectralConv2D(inp, cnum, 2 * cnum)
        self.conv3 = SpectralConv2D(inp, 2 * cnum, 4 * cnum)
        self.conv4 = SpectralConv2D(inp, 4 * cnum, 4 * cnum)
        self.conv5 = SpectralConv2D(inp, 4 * cnum, 4 * cnum)
        self.conv6 = SpectralConv2D(inp, 4 * cnum, 4 * cnum)
        self.flatten = Flatten()

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        x = self.conv5(x)
        x = self.conv6(x)
        x = self.flatten(x)
        return x




class Flatten(nn.Module):
    def forward(self, input):
        return input.view(input.size(0), -1)