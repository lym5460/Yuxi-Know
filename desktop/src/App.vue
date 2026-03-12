<template>
  <a-config-provider :theme="themeConfig">
    <router-view />
  </a-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import { theme } from 'ant-design-vue'

const themeConfig = computed(() => ({
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#00d4ff',
    colorBgBase: '#0a0e17',
    colorTextBase: '#e4eaf2',
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
