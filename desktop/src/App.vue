<template>
  <a-config-provider :theme="themeConfig">
    <router-view />
  </a-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import { theme } from 'ant-design-vue'

const themeConfig = computed(() => ({
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#4080ff',
    borderRadius: 8
  }
}))
</script>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
</style>
