<template>
  <div class="max-w-2xl mx-auto px-6 py-12 text-gray-300">
    <h1 class="text-3xl font-bold text-white mb-2">Privacy Policy</h1>
    <p class="text-gray-500 text-sm mb-10">Last updated: May 2026</p>

    <section class="mb-8">
      <h2 class="text-xl font-semibold text-white mb-3">What this app does</h2>
      <p>
        Who's That Seiyuu helps you discover which voice actors from a new anime you've already
        heard in anime you've previously watched. It does this by reading your MyAnimeList watch
        history and cross-referencing voice actor and character data from MyAnimeList.
      </p>
      <p class="mt-3 text-sm text-gray-500">
        This app is not affiliated with or endorsed by MyAnimeList Co., Ltd. Anime and voice actor
        data is retrieved through the official MyAnimeList API and is used in accordance with the
        <a
          href="https://myanimelist.net/static/apiagreement.html"
          target="_blank"
          rel="noopener"
          class="underline hover:text-white"
        >MAL API License Agreement</a>.
      </p>
    </section>

    <section class="mb-8">
      <h2 class="text-xl font-semibold text-white mb-3">What data we collect</h2>
      <ul class="list-disc list-inside space-y-2">
        <li>Your MyAnimeList user ID and username</li>
        <li>Your MyAnimeList OAuth access token (encrypted at rest)</li>
        <li>Your anime watch history as returned by the MAL API</li>
        <li>A session token stored in an HTTP-only cookie to keep you logged in</li>
      </ul>
      <p class="mt-3">We do not collect your email address, password, or any payment information.</p>
    </section>

    <section class="mb-8">
      <h2 class="text-xl font-semibold text-white mb-3">Why we collect it</h2>
      <ul class="list-disc list-inside space-y-2">
        <li>To authenticate you via MyAnimeList OAuth</li>
        <li>To fetch and display your watch history and voice actor overlap data</li>
        <li>To keep your session active between visits</li>
      </ul>
      <p class="mt-3">We do not sell, share, or transfer your data to any third party.</p>
    </section>

    <section class="mb-8">
      <h2 class="text-xl font-semibold text-white mb-3">Cookies</h2>
      <p>
        We use a single HTTP-only session cookie to keep you logged in. This cookie is strictly
        necessary for the app to function and does not track you across other websites. No
        analytics, advertising, or third-party cookies are used.
      </p>
    </section>

    <section class="mb-8">
      <h2 class="text-xl font-semibold text-white mb-3">Data retention</h2>
      <p>
        Your data is stored for as long as you have an account. To delete your account and all
        associated data, contact us at the address below. We will process deletion requests within
        30 days.
      </p>
    </section>

    <section class="mb-8">
      <h2 class="text-xl font-semibold text-white mb-3">Your rights</h2>
      <p>
        Under GDPR (if you are in the EU/EEA) you have the right to access, correct, and delete
        your personal data. To exercise any of these rights, contact us at the address below.
      </p>
    </section>

    <section class="mb-8">
      <h2 class="text-xl font-semibold text-white mb-3">Contact</h2>
      <p>
        This app is a personal project. For any privacy-related questions or deletion requests,
        contact:
        <a href="mailto:filipkjagiela@gmail.com" class="underline hover:text-white">filipkjagiela@gmail.com</a>
      </p>
    </section>

    <div class="mt-10 pt-6 border-t border-gray-800 text-center">
      <NuxtLink to="/" class="text-sm text-gray-500 hover:text-white">Back to home</NuxtLink>
    </div>
  </div>
</template>
