/**
 * 📍 AddressAutocomplete — Champ d'adresse avec suggestions automatiques.
 *
 * Utilise l'API Photon (OpenStreetMap) :
 *   - 100% gratuit, pas de clé API
 *   - CORS ouvert, pas besoin de proxy backend
 *   - Couvre FR, BE, LU, NL et toute l'Europe
 *   - Doc : https://photon.komoot.io
 *
 * UX :
 *   - L'utilisateur tape une adresse → suggestions après 500ms (debounce)
 *   - Tap sur une suggestion → remplit l'adresse complète + code postal + ville
 *   - Si onSelectPostalAndCity n'est pas fourni, seul le champ texte est rempli
 */
import React, { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/src/theme";

type PhotonProperties = {
  name?: string;
  street?: string;
  housenumber?: string;
  postcode?: string;
  city?: string;
  town?: string;
  village?: string;
  state?: string;
  country?: string;
  countrycode?: string;
  osm_id?: number;
};

type PhotonFeature = {
  type: "Feature";
  properties: PhotonProperties;
  geometry?: { type: string; coordinates: number[] };
};

export function AddressAutocomplete({
  value,
  onChangeText,
  onSelect,
  placeholder,
  placeholderTextColor,
  style,
  testID,
  /**
   * Pays prioritaires pour les résultats. Photon n'a pas de filtre strict,
   * mais on peut booster certains pays via le param `lang` + `bias`.
   */
  countries = ["be", "fr", "lu", "nl"],
  /** Langue des résultats (défaut : fr). */
  lang = "fr",
}: {
  value: string;
  onChangeText: (text: string) => void;
  onSelect?: (data: {
    fullAddress: string;
    street?: string;
    postalCode?: string;
    city?: string;
    country?: string;
  }) => void;
  placeholder?: string;
  placeholderTextColor?: string;
  style?: any;
  testID?: string;
  countries?: string[];
  lang?: string;
}) {
  const [suggestions, setSuggestions] = useState<PhotonFeature[]>([]);
  const [loading, setLoading] = useState(false);
  const [showList, setShowList] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastQueryRef = useRef<string>("");

  // Photon API call avec debounce 500ms
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const trimmed = value.trim();
    if (trimmed.length < 3) {
      setSuggestions([]);
      setShowList(false);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      if (lastQueryRef.current === trimmed) return; // évite double-fetch
      lastQueryRef.current = trimmed;
      setLoading(true);
      try {
        const url =
          `https://photon.komoot.io/api/?q=${encodeURIComponent(trimmed)}` +
          `&limit=5&lang=${lang}`;
        const res = await fetch(url, {
          headers: { Accept: "application/json" },
        });
        if (!res.ok) throw new Error(`Photon ${res.status}`);
        const json = await res.json();
        const features: PhotonFeature[] = (json.features || []).filter(
          (f: PhotonFeature) => {
            const cc = (f.properties.countrycode || "").toLowerCase();
            return countries.length === 0 || countries.includes(cc);
          },
        );
        setSuggestions(features);
        setShowList(features.length > 0);
      } catch {
        setSuggestions([]);
        setShowList(false);
      } finally {
        setLoading(false);
      }
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [value, lang, countries.join(",")]);

  const formatFeature = (f: PhotonFeature): string => {
    const p = f.properties;
    const streetPart = [p.housenumber, p.street || p.name]
      .filter(Boolean)
      .join(" ");
    const cityPart = p.city || p.town || p.village || "";
    const postal = p.postcode || "";
    const country = p.country || "";
    return [streetPart, [postal, cityPart].filter(Boolean).join(" "), country]
      .filter(Boolean)
      .join(", ");
  };

  const handlePick = (f: PhotonFeature) => {
    const p = f.properties;
    const streetPart = [p.housenumber, p.street || p.name]
      .filter(Boolean)
      .join(" ");
    const cityPart = p.city || p.town || p.village || "";
    const fullAddress = formatFeature(f);
    onChangeText(streetPart || fullAddress);
    onSelect?.({
      fullAddress,
      street: streetPart || undefined,
      postalCode: p.postcode || undefined,
      city: cityPart || undefined,
      country: p.country || undefined,
    });
    setSuggestions([]);
    setShowList(false);
  };

  return (
    <View>
      <View style={localStyles.inputWrap}>
        <TextInput
          testID={testID}
          value={value}
          onChangeText={(t) => {
            onChangeText(t);
            if (t.length >= 3) setShowList(true);
          }}
          onFocus={() => {
            if (suggestions.length > 0) setShowList(true);
          }}
          placeholder={placeholder}
          placeholderTextColor={placeholderTextColor}
          autoCapitalize="words"
          autoCorrect={false}
          style={style}
        />
        {loading && (
          <ActivityIndicator
            size="small"
            color={colors.primary}
            style={localStyles.spinner}
          />
        )}
      </View>

      {showList && suggestions.length > 0 && (
        <View style={localStyles.dropdown}>
          <FlatList
            data={suggestions}
            keyExtractor={(item, idx) =>
              `${item.properties.osm_id ?? idx}-${idx}`
            }
            keyboardShouldPersistTaps="handled"
            renderItem={({ item }) => (
              <TouchableOpacity
                onPress={() => handlePick(item)}
                style={localStyles.suggestionRow}
                activeOpacity={0.7}
                testID={`address-suggestion-${item.properties.osm_id ?? ""}`}
              >
                <Ionicons
                  name="location"
                  size={16}
                  color={colors.primary}
                  style={{ marginRight: 8 }}
                />
                <Text style={localStyles.suggestionText} numberOfLines={2}>
                  {formatFeature(item)}
                </Text>
              </TouchableOpacity>
            )}
            ItemSeparatorComponent={() => (
              <View style={localStyles.separator} />
            )}
            style={{ maxHeight: 240 }}
          />
        </View>
      )}
    </View>
  );
}

const localStyles = StyleSheet.create({
  inputWrap: {
    position: "relative",
  },
  spinner: {
    position: "absolute",
    right: 12,
    top: 16,
  },
  dropdown: {
    backgroundColor: "#1c1c1e",
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: 10,
    marginTop: 4,
    overflow: "hidden",
  },
  suggestionRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 11,
  },
  suggestionText: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: 14,
    lineHeight: 18,
  },
  separator: {
    height: 1,
    backgroundColor: colors.borderStrong,
    opacity: 0.4,
  },
});
