import { defineConfig } from 'vite'
import { resolve } from 'node:path'

// https://vite.dev/config/
//
// This repo supports two build targets:
// - mode=backend: build output goes to repo-level ../app and uses base '/app/'
//                (served by the FastAPI backend at /app/)
// - default (static): build output goes to ./dist and uses base '/'
//                     (deploy to Vercel/Netlify/static hosting)
export default defineConfig(({ mode }) => {
  const isBackend = mode === 'backend'
  const isWatch = process.env.ROLLUP_WATCH === 'true'

  return {
    base: isBackend ? '/app/' : '/',
    build: {
      outDir: isBackend ? '../app' : 'dist',
      // In backend mode we often run `vite build --watch`. In watch mode, Rollup may rebuild
      // only a subset of inputs; emptying the outDir would delete other HTML pages and cause
      // intermittent 404s from the backend static server.
      emptyOutDir: isBackend ? !isWatch : true,
      rollupOptions: {
        input: {
          index: resolve(__dirname, 'index.html'),
          dashboard: resolve(__dirname, 'dashboard.html'),
          login: resolve(__dirname, 'login.html'),
          subscribe: resolve(__dirname, 'subscribe.html'),
          features: resolve(__dirname, 'features.html'),
          howItWorks: resolve(__dirname, 'how-it-works.html'),
          examples: resolve(__dirname, 'examples.html'),
          pricing: resolve(__dirname, 'pricing.html'),
          support: resolve(__dirname, 'support.html'),
          blogIndex: resolve(__dirname, 'blog/index.html'),
          blogHowToBuildWebsiteUsingAi: resolve(__dirname, 'blog/how-to-build-a-website-using-ai.html'),
          blogLearnCodingWithAiNoExperience: resolve(__dirname, 'blog/learn-coding-with-ai-without-experience.html'),
          blogAiWebsiteBuilderVsTraditionalCoding: resolve(__dirname, 'blog/ai-website-builder-vs-traditional-coding.html'),
          blogStudentsBuildRealProjectsFasterAiTools: resolve(
            __dirname,
            'blog/how-students-can-build-real-projects-faster-using-ai-tools.html',
          ),
          blogBuildWebAppWithoutCodingAiMythOrReality: resolve(
            __dirname,
            'blog/build-a-web-app-without-coding-using-ai-myth-or-reality.html',
          ),
          blogBestAiToolsForStudentsLearnWebDevelopment: resolve(
            __dirname,
            'blog/best-ai-tools-for-students-to-learn-web-development.html',
          ),
          blogFromIdeaToWebsiteAiBuildAppsFaster: resolve(
            __dirname,
            'blog/from-idea-to-website-how-ai-helps-you-build-apps-faster.html',
          ),
          blogWhyLearningWithAiFutureCodingEducation: resolve(
            __dirname,
            'blog/why-learning-with-ai-is-the-future-of-coding-education.html',
          ),
          blogFirstWebAppUsingAiIn30Minutes: resolve(
            __dirname,
            'blog/how-to-create-your-first-web-app-using-ai-in-30-minutes.html',
          ),
          blogAiForBeginnersNonTechnicalBuildWebsites: resolve(
            __dirname,
            'blog/ai-for-beginners-how-non-technical-users-can-build-websites.html',
          ),
        },
      },
    },
  }
})
