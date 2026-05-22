/**
 * Image picker + compression helpers.
 * - Pickers (camera + gallery) with contextual permission handling
 * - Compression via expo-image-manipulator (quality 0.6, max width 1280px)
 * - Returns base64 (raw, no data: prefix) ready to POST
 */
import * as ImagePicker from 'expo-image-picker';
import * as ImageManipulator from 'expo-image-manipulator';
import { Alert, Linking } from 'react-native';

export type PickedImage = {
  base64: string;       // raw base64 (no data URI prefix)
  width: number;
  height: number;
  uri: string;          // local URI after compression (for instant preview)
};

const MAX_WIDTH = 1280;
const COMPRESS_QUALITY = 0.6;

async function compressToBase64(uri: string): Promise<PickedImage> {
  const result = await ImageManipulator.manipulateAsync(
    uri,
    [{ resize: { width: MAX_WIDTH } }],
    {
      compress: COMPRESS_QUALITY,
      format: ImageManipulator.SaveFormat.JPEG,
      base64: true,
    }
  );
  return {
    base64: result.base64 || '',
    width: result.width,
    height: result.height,
    uri: result.uri,
  };
}

async function ensurePermission(
  request: () => Promise<ImagePicker.PermissionResponse>,
  current: () => Promise<ImagePicker.PermissionResponse>,
  context: 'camera' | 'gallery',
): Promise<boolean> {
  let res = await current();
  if (res.status === 'granted') return true;
  if (res.canAskAgain) {
    res = await request();
    if (res.status === 'granted') return true;
  }
  // Permanently denied — guide to settings
  const labels = {
    camera: { title: 'Caméra refusée', body: "L'accès à la caméra est nécessaire pour photographier vos chantiers." },
    gallery: { title: 'Galerie refusée', body: "L'accès à la galerie est nécessaire pour joindre vos photos de chantier." },
  } as const;
  Alert.alert(
    labels[context].title,
    labels[context].body,
    [
      { text: 'Annuler', style: 'cancel' },
      { text: 'Ouvrir les réglages', onPress: () => Linking.openSettings() },
    ],
  );
  return false;
}

export async function pickFromCamera(): Promise<PickedImage | null> {
  const ok = await ensurePermission(
    ImagePicker.requestCameraPermissionsAsync,
    ImagePicker.getCameraPermissionsAsync,
    'camera',
  );
  if (!ok) return null;
  const result = await ImagePicker.launchCameraAsync({
    mediaTypes: ['images'],
    quality: 1,
    exif: false,
  });
  if (result.canceled || !result.assets?.length) return null;
  return await compressToBase64(result.assets[0].uri);
}

export async function pickFromGallery(): Promise<PickedImage | null> {
  const ok = await ensurePermission(
    ImagePicker.requestMediaLibraryPermissionsAsync,
    ImagePicker.getMediaLibraryPermissionsAsync,
    'gallery',
  );
  if (!ok) return null;
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ['images'],
    quality: 1,
    exif: false,
    allowsEditing: false,
  });
  if (result.canceled || !result.assets?.length) return null;
  return await compressToBase64(result.assets[0].uri);
}

/** Pick a logo (square crop allowed, no caption). Reused from gallery only. */
export async function pickLogo(): Promise<PickedImage | null> {
  const ok = await ensurePermission(
    ImagePicker.requestMediaLibraryPermissionsAsync,
    ImagePicker.getMediaLibraryPermissionsAsync,
    'gallery',
  );
  if (!ok) return null;
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ['images'],
    quality: 1,
    allowsEditing: true,
    aspect: [1, 1],
    exif: false,
  });
  if (result.canceled || !result.assets?.length) return null;
  // Compress logos smaller — keep them tiny
  const manipulated = await ImageManipulator.manipulateAsync(
    result.assets[0].uri,
    [{ resize: { width: 512 } }],
    { compress: 0.85, format: ImageManipulator.SaveFormat.PNG, base64: true },
  );
  return {
    base64: manipulated.base64 || '',
    width: manipulated.width,
    height: manipulated.height,
    uri: manipulated.uri,
  };
}
