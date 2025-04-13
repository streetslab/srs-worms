import numpy as np
import cv2
from scipy.interpolate import splprep
from scipy.interpolate import splev
from skimage.measure import label

def get_border_path(mask):
    """
    Find the border path of a binary mask.

    Parameters
    ----------
    mask : np.ndarray
        The binary mask to find the border path of.
    """
    contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    path = max(contours[0], key=cv2.contourArea)
    path = path.squeeze()
    return path

def get_endpoint_idx(path, space=50, second=False):
    """
    Find the endpoint of a path by comparing the angles between the path and its shifted versions.
    The endpoint is the point with the smallest angle between the path and the shifted path.

    Parameters
    ----------
    path : np.ndarray
        The path to find the endpoint of.
    space : int
        The number of points to shift the path by.
    second : bool
        If True, return the second endpoint of the path.
    """
    path_forward = np.concatenate([path[-space:], path[:-space]])
    path_backward = np.concatenate([path[space:], path[:space]])
    vector_forward = path_forward - path
    vector_backward = path_backward - path
    dot_product = np.sum(vector_forward * vector_backward, axis=1)
    angles = np.clip(dot_product / (np.linalg.norm(vector_forward, axis=1) * np.linalg.norm(vector_backward, axis=1)), -1, 1)
    angles = np.arccos(angles)
    idx = np.argmin(angles)
    if second:
        return idx, get_second_endpoint(path, angles, idx)
    return idx 

def get_second_endpoint(path, angles, idx):
    """
    Find the second endpoint of a path, using the angle information, as well as the first endpoint.
    
    Parameters
    ----------
    path : np.ndarray
        The path to find the second endpoint of.
    angles : np.ndarray
        The angles between the path and its shifted versions.
    idx : int
        The index of the first endpoint.
    """
    skip = len(path) // 4
    reordered_path = np.concatenate([path[idx:], path[:idx]])
    reordered_angles = np.concatenate([angles[idx:], angles[:idx]])
    second_idx = np.argmin(reordered_angles[skip:-skip])
    coordinate = reordered_path[second_idx + skip]
    second_idx = np.where((path == coordinate).all(axis=1))[0][0]
    return second_idx

def check_head(path, idx, second_idx, ant_mask):
    """
    Check if the endpoint of the path is the head of the worm, by comparing the distance between the endpoint and the head
    to the distance between the endpoint and the tail.

    Parameters
    ----------
    path : np.ndarray
        The path to check the head of.
    idx : int
        The index of the first endpoint.
    second_idx : int
        The index of the second endpoint.
    ant_mask : np.ndarray
        The mask of the worm's anterior part.

    Returns
    -------
    head_idx : int
        The index of the head (anchor point).
    tail_idx : int
        The index of the tail.
    """
    anchor = path[idx]
    head_idx = idx
    tail_idx = second_idx
    if ant_mask[anchor[1], anchor[0]] == 0:
        head_idx = second_idx
        tail_idx = idx
        anchor = path[second_idx]
    return head_idx, tail_idx

def resample_path(path, num_points=5000):
    """
    Resample a path (interpolate) to have a fixed number of points.
    
    Parameters
    ----------
    path : np.ndarray
        The path to resample.
    num_points : int
        The number of points to resample the path to.
    """
    tck, u = splprep(path.T, s=0)  # tck are the spline parameters
    unew = np.linspace(0, 1, num_points)
    out = splev(unew, tck)
    return np.vstack(out).T

def get_spline(path, head_idx, tail_idx):
    """
    Get the middle spline of a worm.

    Parameters
    ----------
    path : np.ndarray
        The path of the worm.
    head_idx : int
        The index of the head.
    tail_idx : int
        The index of the tail.
    """
    small_idx, large_idx = sorted([head_idx, tail_idx])
    first_half = path[small_idx:large_idx]
    second_half = np.concatenate([path[large_idx:], path[:small_idx]])[::-1]
    avg_path = (resample_path(first_half) + resample_path(second_half)) / 2
    anchor = path[head_idx]
    if np.linalg.norm(avg_path[0] - anchor) > np.linalg.norm(avg_path[-1] - anchor): # reverse the path, so head_idx is 0
        avg_path = avg_path[::-1]
    return avg_path

def get_quantile_point(path, quantile=0.1):
    """
    Get the point on a path that is at a certain quantile of the path's length.

    Parameters
    ----------
    path : np.ndarray
        The path to find the quantile point of.
    quantile : float
        The quantile of the path's length to find the point at
    """
    cum_distance = np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))
    q_point_idx = np.argmin(np.abs(cum_distance - cum_distance[-1] * quantile))
    return q_point_idx

def divide_mask(mask, path, mid_point_idx, space=50, multiplier=6):
    """
    Divide a mask into two parts, using a line perpendicular to the path at a certain point.

    Parameters
    ----------
    mask : np.ndarray
        The mask to divide.
    path : np.ndarray
        The path to use to divide the mask.
    mid_point_idx : int
        The index of the point on the path to use to divide the mask.
    space : int
        The number of points to shift, to create the parallel line.
    multiplier : int
        The multiplier to use to extend the normal line.
    """
    temp = mask.copy()
    x1, y1 = path[mid_point_idx]
    x2, y2 = path[mid_point_idx + space]
    normal_vector = np.array([y2 - y1, x1 - x2])
    xn1, yn1 = x1 + multiplier * normal_vector[0], y1 + multiplier * normal_vector[1]
    xn2, yn2 = x1 - multiplier * normal_vector[0], y1 - multiplier * normal_vector[1]
    cv2.line(temp, (int(xn1), int(yn1)), (int(xn2), int(yn2)), 0, 2)
    return temp

def select_mask(mask, anchor):
    """
    Select the part of a mask (with same label) that is closer to a certain point. Background is label 0.

    Parameters
    ----------
    mask : np.ndarray
        The mask to select the part of.
    anchor : tuple
        The point to use to select the part of the mask.
    """
    temp = mask.copy()
    labels = np.unique(temp)
    for label_ in labels:
        if label_ == 0:
            continue
        mask_ = temp == label_
        if mask_[anchor[1], anchor[0]] == 0:
            temp[temp == label_] = 0
    return temp

def get_worm_masks(mask, ant_mask, quantile=0.13):
    """
    Get the anterior and posterior masks of a worm.

    Parameters
    ----------
    mask : np.ndarray
        The mask to get the anterior and posterior masks of.
    quantile : float
        The quantile of the path's length to use to divide the mask.
    """
    border = get_border_path(mask)
    head_idx, tail_idx = get_endpoint_idx(border, second=True)
    head_idx, tail_idx = check_head(border, head_idx, tail_idx, ant_mask)
    spline = get_spline(border, head_idx, tail_idx)
    mid_point_idx = get_quantile_point(spline, quantile)
    labeled_mask = label(divide_mask(mask, spline, mid_point_idx) > 0)
    ant_mask = select_mask(labeled_mask, border[head_idx])
    post_mask = select_mask(labeled_mask, border[tail_idx])
    return ant_mask, post_mask
