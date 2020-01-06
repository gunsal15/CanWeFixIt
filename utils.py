import cv2
import numpy as np
import torch


def random_bbox(width=128, height=128, vertical_margin=0, horizontal_margin=0, img_shape=(256, 256, 3)):
    """Generate a random tlhw.
    Returns:
        tuple: (top, left, height, width)
    """
    img_shape = img_shape
    img_height = img_shape[0]
    img_width = img_shape[1]
    maxt = img_height - vertical_margin - height
    maxl = img_width - horizontal_margin - width
    t = torch.tensor(0, dtype=torch.int32).random_(vertical_margin, maxt)
    l = torch.tensor(0, dtype=torch.int32).random_(horizontal_margin, maxl)
    h = torch.tensor(height, dtype=torch.int32)
    w = torch.tensor(width, dtype=torch.int32)
    return t, l, h, w


def brush_stroke_mask(dimensions=(256, 256), min_num_vertex=4, max_num_vertex=12, min_line_width=12, max_line_width=40):
    """ Generate random mask
        Args:
            :param dimensions: tuple, (width, height)
            :param min_num_vertex: int
            :param max_num_vertex: int
            :param min_line_width: int
            :param max_line_width: int
        Returns:
            torch.tensor: output with shape [H, W, 1]
    """
    mean_angle = 2 * np.math.pi / 5
    angle_range = 2 * np.math.pi / 15
    W, H = dimensions

    average_radius = np.math.sqrt(H * H + W * W) / 8
    mask = np.zeros((H, W, 1), np.uint8)

    for _ in range(np.random.randint(1, 4)):
        num_vertex = np.random.randint(min_num_vertex, max_num_vertex)
        angle_min = mean_angle - np.random.uniform(0, angle_range)
        angle_max = mean_angle + np.random.uniform(0, angle_range)
        angles = []
        vertex = []
        for i in range(num_vertex):
            if i % 2 == 0:
                angles.append(2 * np.math.pi - np.random.uniform(angle_min, angle_max))
            else:
                angles.append(np.random.uniform(angle_min, angle_max))

        h, w = mask.shape[:2]
        vertex.append((int(np.random.randint(0, w)), int(np.random.randint(0, h))))
        width = int(np.random.uniform(min_line_width, max_line_width))
        for i in range(1, num_vertex):
            r = np.clip(
                np.random.normal(loc=average_radius, scale=average_radius // 2),
                0, 2 * average_radius)
            new_x = np.clip(vertex[-1][0] + r * np.math.cos(angles[i]), 0, w)
            new_y = np.clip(vertex[-1][1] + r * np.math.sin(angles[i]), 0, h)
            vertex.append((int(new_x), int(new_y)))
            cv2.line(mask, vertex[i - 1], vertex[i], 1, thickness=width)
            cv2.circle(mask, vertex[i], width // 2, 1, thickness=-1)
    if np.random.normal() > 0:
        cv2.flip(mask, 0)
    if np.random.normal() > 0:
        cv2.flip(mask, 1)

    mask = np.asarray(mask, np.float32)
    mask = np.reshape(mask, (1, H, W, 1))
    tensor = torch.tensor(mask)
    tensor = tensor.view([1] + [H, W] + [1])
    return tensor


def bbox2mask(bbox, max_delta_height=32, max_delta_width=32, img_shape=(256, 256, 3)):
    """Generate mask tensor from bbox.
    Args:
        :param bbox: tuple, (top, left, height, width)
        :param max_delta_width: int
        :param max_delta_height: int
        :param img_shape: tuple, (width, height, depth)
    Returns:
        torch.tensor: output with shape [1, H, W, 1]
    """
    height = img_shape[0]
    width = img_shape[1]
    mask = np.zeros((1, height, width, 1), np.float32)

    h = np.random.randint(max_delta_height // 2 + 1)
    w = np.random.randint(max_delta_width // 2 + 1)

    mask[:, bbox[0] + h:bbox[0] + bbox[2] - h, bbox[1] + w:bbox[1] + bbox[3] - w, :] = 1.

    tensor = torch.tensor(mask)
    tensor.view([1] + [height, width] + [1])
    return tensor