"""Speed-adaptive low-pass filter, following the One Euro filter equations.

Algorithm reference: https://gery.casiez.net/1euro/ (Casiez et al., CHI 2012).
Coordinates stay inside the segment between the previous output and current input.
"""
import math


class OneEuroFilter:
    def __init__(self):
        self.reset()

    def reset(self):
        self.raw = self.value = self.timestamp = None
        self.velocity = [0.0, 0.0]

    @staticmethod
    def alpha(cutoff, dt):
        ratio = 2 * math.pi * cutoff * dt
        return ratio / (1 + ratio)

    def update(self, point, now, responsiveness=0.5):
        if self.timestamp is None or now <= self.timestamp or now - self.timestamp > 0.3:
            self.raw = self.value = list(point)
            self.timestamp = now
            self.velocity = [0.0, 0.0]
            return list(point)
        dt = max(0.001, now - self.timestamp)
        derivative_alpha = self.alpha(1.0, dt)
        derivative = [(p - r) / dt for p, r in zip(point, self.raw)]
        self.velocity = [derivative_alpha * d + (1 - derivative_alpha) * v
                         for d, v in zip(derivative, self.velocity)]
        cutoff = (0.6 + 2.4 * responsiveness) + (4 + 20 * responsiveness) * math.hypot(*self.velocity)
        alpha = self.alpha(cutoff, dt)
        self.value = [v + alpha * (p - v) for p, v in zip(point, self.value)]
        self.raw = list(point)
        self.timestamp = now
        return list(self.value)
