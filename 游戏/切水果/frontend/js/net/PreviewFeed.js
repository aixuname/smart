/** Pulls the existing server preview only while a visible consumer needs it. */
export class PreviewFeed {
  constructor(image, { interval = 150, onState = () => {} } = {}) {
    this.image = image;
    this.interval = interval;
    this.onState = onState;
    this.active = false;
    this.destroyed = false;
    this.request = null;
    this.timer = null;
    this.imageUrl = null;
  }

  setActive(active) {
    active = !!active;
    if (this.destroyed || active === this.active) return;
    this.active = active;
    if (active) {
      this._poll();
      return;
    }
    clearTimeout(this.timer);
    this.timer = null;
    const request = this.request;
    this.request = null;
    if (request) {
      clearTimeout(request.timeout);
      request.controller.abort();
    }
    this._clearImage();
    this.onState(false, null);
  }

  _isCurrent(request) {
    return this.active && this.request === request && !request.controller.signal.aborted;
  }

  _clearImage() {
    this.image.removeAttribute('src');
    if (this.imageUrl) URL.revokeObjectURL(this.imageUrl);
    this.imageUrl = null;
  }

  async _load(request) {
    const response = await fetch('/api/preview.jpg', {
      cache: 'no-store', signal: request.controller.signal,
    });
    if (!response.ok) throw new Error('Preview unavailable');
    let gesture = null;
    try {
      const value = JSON.parse(response.headers.get('X-Preview-Gesture'));
      if (value && typeof value === 'object' && !Array.isArray(value)) gesture = value;
    } catch (_) { /* Older servers and missing metadata still provide a usable image. */ }
    const blob = await response.blob();
    if (!this._isCurrent(request)) return;
    const previousUrl = this.imageUrl;
    this.imageUrl = URL.createObjectURL(blob);
    this.image.src = this.imageUrl;
    if (previousUrl) URL.revokeObjectURL(previousUrl);
    await this.image.decode();
    return gesture;
  }

  async _poll() {
    if (!this.active || this.request) return;
    this.timer = null;
    const request = { controller: new AbortController(), timeout: null };
    this.request = request;
    const { signal } = request.controller;
    let rejectAbort;
    const aborted = new Promise((_, reject) => {
      rejectAbort = () => reject(new Error('Preview cancelled'));
      signal.addEventListener('abort', rejectAbort, { once: true });
    });
    request.timeout = setTimeout(() => request.controller.abort(), 2000);
    try {
      // Aborting fetch alone cannot release a stalled image decode.
      const gesture = await Promise.race([this._load(request), aborted]);
      if (this._isCurrent(request)) this.onState(true, gesture);
    } catch (_) {
      if (this.active && this.request === request) {
        this._clearImage();
        this.onState(false, null);
      }
    } finally {
      clearTimeout(request.timeout);
      signal.removeEventListener('abort', rejectAbort);
      // An earlier session must never clear or reschedule a newer request.
      if (this.request === request) {
        this.request = null;
        if (this.active) this.timer = setTimeout(() => this._poll(), this.interval);
      }
    }
  }

  destroy() {
    this.setActive(false);
    this.destroyed = true;
  }
}
