"""A club-coloured radar based on the exact restored observation."""

import cv2


def draw_radar(frame, observation, home_bgr, away_bgr):
    height, width = frame.shape[:2]
    scale = width / 1280
    w, h = round(220 * scale), round(130 * scale)
    x, y = width - w - round(24 * scale), height - h - round(24 * scale)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (54, 29, 12), -1)
    cv2.rectangle(frame, (x + 8, y + 8), (x + w - 8, y + h - 8), (150, 160, 155), 1)
    cv2.line(frame, (x + w // 2, y + 8), (x + w // 2, y + h - 8), (150, 160, 155), 1)
    cv2.circle(frame, (x + w // 2, y + h // 2), round(20 * scale), (150, 160, 155), 1)

    def pixel(position):
        return (
            x + 8 + round((float(position[0]) + 1) / 2 * (w - 16)),
            y + 8 + round((float(position[1]) + 0.44) / 0.88 * (h - 16)),
        )

    for key, colour in (("left_team", home_bgr), ("right_team", away_bgr)):
        for position in observation[key]:
            point = pixel(position)
            cv2.circle(frame, point, max(3, round(4 * scale)), (240, 240, 240), -1)
            cv2.circle(frame, point, max(2, round(3 * scale)), colour, -1)
    cv2.circle(frame, pixel(observation["ball"]), max(2, round(2 * scale)), (255, 255, 255), -1)
    return frame
