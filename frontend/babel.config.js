module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      // Required for react-native-vision-camera v4 frame processors.
      // Must come before the Reanimated/worklets plugin auto-added by
      // babel-preset-expo (Expo 54 auto-detects react-native-worklets).
      'react-native-worklets-core/plugin',
    ],
  };
};
