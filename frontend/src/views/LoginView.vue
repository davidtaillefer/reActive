<template>
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <h3 v-if="!isRegister">Login</h3>
                <h3 v-else>Create account</h3>

                <div class="mb-3">
                    <a href="#" @click.prevent="toggleRegister()">{{ isRegister ? 'Back to login' : 'Create account'
                        }}</a>
                </div>

                <form v-if="!isRegister" @submit.prevent="submit">
                    <div class="mb-3">
                        <label class="form-label">Username</label>
                        <input v-model="username" class="form-control" />
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Password</label>
                        <input v-model="password" type="password" class="form-control" />
                    </div>
                    <div v-if="error" class="alert alert-danger">{{ error }}</div>
                    <button class="btn btn-primary" type="submit">Login</button>
                </form>

                <form v-else @submit.prevent="register">
                    <div class="mb-3">
                        <label class="form-label">Username</label>
                        <input v-model="username" class="form-control" />
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Email (optional)</label>
                        <input v-model="email" type="email" class="form-control" />
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Password</label>
                        <input v-model="password" type="password" class="form-control" />
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Confirm password</label>
                        <input v-model="confirm" type="password" class="form-control" />
                    </div>
                    <div v-if="error" class="alert alert-danger">{{ error }}</div>
                    <button class="btn btn-primary" type="submit">Create account</button>
                </form>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: 'LoginView',
    data() {
        return { username: '', password: '', email: '', confirm: '', error: null, isRegister: false }
    },
    methods: {
        async submit() {
            this.error = null
            try {
                const base = import.meta.env.VITE_API_BASE_URL || '/'
                const baseNormalized = base.endsWith('/') ? base : base + '/'
                const res = await fetch(`${baseNormalized}auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ username: this.username, password: this.password })
                })
                const data = await res.json()
                if (!res.ok) {
                    this.error = data.error || 'Login failed'
                    return
                }
                // On success, navigate home
                this.$router.push({ name: 'Calendar' })
            } catch (e) {
                this.error = 'Network error'
            }
        },

        async register() {
            this.error = null
            if (!this.username || !this.password) {
                this.error = 'username and password required'
                return
            }
            if (this.password !== this.confirm) {
                this.error = 'passwords do not match'
                return
            }

            try {
                const base = import.meta.env.VITE_API_BASE_URL || '/'
                const baseNormalized = base.endsWith('/') ? base : base + '/'
                const res = await fetch(`${baseNormalized}auth/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ username: this.username, password: this.password, email: this.email })
                })
                const data = await res.json()
                if (!res.ok) {
                    this.error = data.error || 'Registration failed'
                    return
                }
                // On success, navigate home
                this.$router.push({ name: 'Calendar' })
            } catch (e) {
                this.error = 'Network error'
            }
        },

        toggleRegister() {
            this.error = null
            this.isRegister = !this.isRegister
        }
    }
}
</script>

<style scoped>
.container {
    max-width: 720px;
}
</style>
