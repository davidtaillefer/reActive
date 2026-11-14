import { defineStore } from 'pinia'

export const usePreferencesStore = defineStore('preferences', {
  state: () => ({
    userId: localStorage.getItem('userId') || crypto.randomUUID(),

    units: 'metric',
    defaultColourMode: 'none',
    climbFocusSync: true,

    maxHr: null,
    restingHr: null,
    ftp: null,

    loaded: false
  }),

  actions: {
    async load() {
      localStorage.setItem('userId', this.userId)

      const res = await fetch('/preferences', {
        headers: {
          'X-User-Id': this.userId
        }
      })

      const data = await res.json()
      const prefs = data.preferences || {}

      Object.assign(this, {
        ...prefs,
        defaultColourMode: prefs.default_colour_mode ?? prefs.defaultColourMode ?? this.defaultColourMode,
        climbFocusSync: prefs.climb_focus_sync ?? prefs.climbFocusSync ?? this.climbFocusSync,
        maxHr: prefs.max_hr ?? prefs.maxHr ?? this.maxHr,
        restingHr: prefs.resting_hr ?? prefs.restingHr ?? this.restingHr,
        ftp: prefs.ftp ?? this.ftp,
      })
      this.loaded = true
    },

    async save() {
      await fetch('/preferences', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': this.userId
        },
        body: JSON.stringify({
          units: this.units,
          default_colour_mode: this.defaultColourMode,
          climb_focus_sync: this.climbFocusSync,
          max_hr: this.maxHr,
          resting_hr: this.restingHr,
          ftp: this.ftp
        })
      })

      // also persist locally for instant reload
      localStorage.setItem('prefs', JSON.stringify(this.$state))
    }
  }
})