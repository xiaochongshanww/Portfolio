import { createRouter, createWebHistory } from 'vue-router'
import JobList from '../views/JobList.vue'
import ProfileForm from '../views/ProfileForm.vue'
import MatchResult from '../views/MatchResult.vue'
import FavoritesPage from '../views/FavoritesPage.vue'

const routes = [
  { path: '/', redirect: '/jobs' },
  { path: '/jobs', name: 'jobs', component: JobList },
  { path: '/profile', name: 'profile', component: ProfileForm },
  { path: '/match', name: 'match', component: MatchResult },
  { path: '/favorites', name: 'favorites', component: FavoritesPage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
