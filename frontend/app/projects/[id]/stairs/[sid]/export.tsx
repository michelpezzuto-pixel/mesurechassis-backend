/**
 * PHASE 4 — Plan de Balancement & Export
 * URL: /projects/[id]/stairs/[sid]/export
 *
 * Page de validation finale :
 *  - SVG détaillé du balancement (vue de dessus, à l'échelle, avec marches dansantes radiales
 *    dans les quart-tournants, cotations, ligne de foulée)
 *  - KPI cards Blondel temps réel (n marches, h, g, pente) + alerte ergonomie 600-640
 *  - Configuration de l'export : photos / notes / logo + format PDF | DXF | PDF+DXF
 *  - Sticky bottom : MODIFIER LA CONFIGURATION + GÉNÉRER LES LIVRABLES (téléchargement direct)
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, Alert, Platform, Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons, Feather } from '@expo/vector-icons';
import Svg, { Circle, G, Line, Polygon, Rect, Text as SvgText } from 'react-native-svg';
import { Stairs, ApiStair, ApiNiveau, ApiTroncon, StairCompute, Exports } from '@/src/api';
import { getToken } from '@/src/api';
import { C, SP, R, FONT } from '@/src/theme';

type FormatKey = 'pdf' | 'dxf' | 'both';

export default function ExportPage() {
  const { id, sid } = useLocalSearchParams<{ id: string; sid: string }>();
  const router = useRouter();

  const [stair, setStair] = useState<ApiStair | null>(null);
  const [compute, setCompute] = useState<StairCompute | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  // Export options
  const [includePhotos, setIncludePhotos] = useState(true);
  const [includeNotes, setIncludeNotes] = useState(true);
  const [includeLogo, setIncludeLogo] = useState(true);
  const [format, setFormat] = useState<FormatKey>('both');

  const load = useCallback(async () => {
    if (!id || !sid) return;
    try {
      const [s, c] = await Promise.all([Stairs.get(id, sid), Stairs.compute(id, sid)]);
      setStair(s);
      setCompute(c);
    } catch (e: any) {
      Alert.alert('Erreur', e?.response?.data?.detail || 'Chargement impossible');
      router.back();
    } finally {
      setLoading(false);
    }
  }, [id, sid, router]);

  useEffect(() => { load(); }, [load]);

  // Aggregated Blondel for "primary" niveau (the first one with marches)
  const primaryCalc = useMemo(() => {
    if (!compute) return null;
    return compute.niveaux_calc.find(n => n.n_steps_niveau > 0) || compute.niveaux_calc[0] || null;
  }, [compute]);

  const blondelValid = primaryCalc ? primaryCalc.blondel_value >= 600 && primaryCalc.blondel_value <= 640 : true;
  const blondelOutOfRange = primaryCalc ? primaryCalc.blondel_value < 560 || primaryCalc.blondel_value > 670 : false;

  // Download a single URL
  const downloadFile = async (url: string, filename: string) => {
    if (Platform.OS === 'web') {
      // Inject auth via fetch + blob, then open
      const t = await getToken();
      const r = await fetch(url, { headers: t ? { Authorization: `Bearer ${t}` } : {} });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const blobUrl = URL.createObjectURL(blob);
      // Trigger download via anchor click (web only) — guarded with typeof document
      if (typeof document !== 'undefined') {
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = filename;
        a.click();
      } else {
        Linking.openURL(blobUrl);
      }
      setTimeout(() => URL.revokeObjectURL(blobUrl), 4000);
    } else {
      // Native : need auth header → open via signed URL is not possible; use Linking with token
      // For MVP, open the URL directly (works in dev because token is on the same origin via fetch)
      // A robust solution would use expo-file-system + downloadAsync; keeping simple here.
      const t = await getToken();
      // We can append a header-free URL only if the API supports cookie. For now: alert.
      try {
        await Linking.openURL(url);
      } catch {
        Alert.alert('Téléchargement', `Ouvrez ce lien depuis votre navigateur :\n${url}`);
      }
    }
  };

  const generate = async () => {
    if (!stair) return;
    setGenerating(true);
    try {
      const safeName = stair.name.replace(/[^a-z0-9_-]/gi, '_').toLowerCase();
      if (format === 'pdf' || format === 'both') {
        const url = Exports.pdfUrl(id!, {
          stair_id: sid,
          include_photos: includePhotos,
          include_notes: includeNotes,
          include_logo: includeLogo,
        });
        await downloadFile(url, `escalier_${safeName}.pdf`);
      }
      if (format === 'dxf' || format === 'both') {
        const url = Exports.dxfUrl(id!, { stair_id: sid });
        await downloadFile(url, `escalier_${safeName}.dxf`);
      }
      Alert.alert(
        'Livrables générés ✓',
        format === 'both' ? 'PDF et DXF téléchargés.' : format === 'pdf' ? 'PDF téléchargé.' : 'DXF téléchargé.',
      );
    } catch (e: any) {
      Alert.alert('Erreur', e?.message || 'Génération impossible');
    } finally {
      setGenerating(false);
    }
  };

  if (loading || !stair || !compute) {
    return (
      <SafeAreaView style={[styles.safe, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator color={C.ACCENT} size="large" />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.topbar}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={10}>
          <Ionicons name="arrow-back" size={24} color={C.WHITE} />
        </TouchableOpacity>
        <View style={{ flex: 1, alignItems: 'center' }}>
          <Text style={styles.topbarLabel}>PLAN DE BALANCEMENT</Text>
          <Text style={styles.topbarTitle} numberOfLines={1}>{stair.name.toUpperCase()}</Text>
        </View>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: SP.lg, paddingBottom: 130 }}>
        {/* SVG Balancement */}
        <View style={styles.sketchCard}>
          <BalancementSketch stair={stair} compute={compute} />
        </View>

        {/* KPI Blondel (cartes vert pomme) */}
        <Text style={styles.section}>CALCUL BLONDEL TEMPS RÉEL</Text>
        <View style={styles.kpiRow}>
          <KPICard label="MARCHES" value={String(compute.total_steps)} />
          <KPICard label="HAUTEUR h" value={`${Math.round(primaryCalc?.h || 0)}`} unit="mm" />
          <KPICard label="GIRON g" value={`${Math.round(primaryCalc?.g || 0)}`} unit="mm" />
          <KPICard label="PENTE" value={`${Math.round(primaryCalc?.slope_angle || 0)}`} unit="°" />
        </View>

        {/* Blondel alert (orange si hors 600-640, rouge si hors 560-670) */}
        {primaryCalc && (
          <View
            style={[
              styles.blondelBox,
              blondelOutOfRange
                ? styles.blondelBoxError
                : blondelValid
                ? styles.blondelBoxOk
                : styles.blondelBoxWarn,
            ]}
          >
            <Ionicons
              name={blondelOutOfRange ? 'alert-circle' : blondelValid ? 'checkmark-circle' : 'warning'}
              size={22}
              color={blondelOutOfRange ? C.DANGER : blondelValid ? C.ACCENT : C.WARN}
            />
            <View style={{ flex: 1, marginLeft: SP.sm }}>
              <Text
                style={[
                  styles.blondelTitle,
                  { color: blondelOutOfRange ? C.DANGER : blondelValid ? C.ACCENT : C.WARN },
                ]}
              >
                2h+g = {Math.round(primaryCalc.blondel_value)} mm
              </Text>
              <Text style={styles.blondelHint}>
                {blondelOutOfRange
                  ? 'Erreur d\'ergonomie : Loi de Blondel hors plage 560-670 mm. Ajustez la longueur des tronçons ou la hauteur.'
                  : blondelValid
                  ? 'Ergonomie optimale (cible 600-640 mm).'
                  : 'Acceptable mais hors plage idéale 600-640 mm. Ergonomie compromise.'}
              </Text>
            </View>
          </View>
        )}

        {/* Configuration export */}
        <Text style={styles.section}>CONFIGURATION DE L'EXPORT</Text>
        <View style={styles.optsCard}>
          <CheckRow
            label="Inclure photos du chantier"
            icon="camera"
            checked={includePhotos}
            onToggle={() => setIncludePhotos(!includePhotos)}
            testID="opt-photos"
          />
          <CheckRow
            label="Inclure notes terrain"
            icon="document-text"
            checked={includeNotes}
            onToggle={() => setIncludeNotes(!includeNotes)}
            testID="opt-notes"
          />
          <CheckRow
            label="Inclure logo entreprise"
            icon="image"
            checked={includeLogo}
            onToggle={() => setIncludeLogo(!includeLogo)}
            testID="opt-logo"
          />
        </View>

        <Text style={styles.section}>FORMAT D'EXPORT</Text>
        <View style={styles.formatRow}>
          <FormatBtn
            active={format === 'pdf'}
            onPress={() => setFormat('pdf')}
            icon="file-pdf-box"
            label="PDF CLASSIQUE"
            testID="fmt-pdf"
          />
          <FormatBtn
            active={format === 'dxf'}
            onPress={() => setFormat('dxf')}
            icon="floor-plan"
            label="DXF AUTOCAD"
            testID="fmt-dxf"
          />
          <FormatBtn
            active={format === 'both'}
            onPress={() => setFormat('both')}
            icon="package-variant"
            label="PDF + DXF"
            testID="fmt-both"
          />
        </View>
      </ScrollView>

      {/* Sticky bottom */}
      <View style={styles.bottomBar}>
        <TouchableOpacity style={[styles.btn, styles.btnGhost]} onPress={() => router.back()} testID="btn-modify">
          <Feather name="settings" size={16} color={C.WHITE} />
          <Text style={[styles.btnTxt, { color: C.WHITE }]}>MODIFIER LA CONFIG.</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.btn, styles.btnPrimary, generating && { opacity: 0.6 }]}
          onPress={generate}
          disabled={generating}
          testID="btn-generate"
        >
          {generating ? (
            <ActivityIndicator color={C.DARK} />
          ) : (
            <>
              <Ionicons name="download" size={16} color={C.DARK} />
              <Text style={styles.btnTxt}>GÉNÉRER LES LIVRABLES</Text>
            </>
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

// ────────────────────────── SVG BALANCEMENT ──────────────────────────

function BalancementSketch({ stair, compute }: { stair: ApiStair; compute: StairCompute }) {
  // Pour le balancement, on rend chaque niveau séparément sous forme de "vue de dessus".
  // Le 1er niveau avec des tronçons est rendu en grand (ligne de foulée + cotations).
  const primaryNiveau = stair.niveaux.find(n => n.troncons.length > 0);
  if (!primaryNiveau) {
    return (
      <View style={{ padding: SP.lg, alignItems: 'center' }}>
        <MaterialCommunityIcons name="floor-plan" size={48} color={C.GRAY3} />
        <Text style={{ ...FONT.small, marginTop: SP.sm }}>Aucun tronçon défini</Text>
      </View>
    );
  }
  const primaryCalc = compute.niveaux_calc.find(n => n.niveau_id === primaryNiveau.id);
  return (
    <NiveauBalancementSVG niveau={primaryNiveau} calc={primaryCalc} />
  );
}

function NiveauBalancementSVG({ niveau, calc }: { niveau: ApiNiveau; calc: any }) {
  const W = 360, H = 320;
  const PAD = 36;

  // Walk tronçons, tracking position & direction. dir: 0=right, 1=up, 2=left, 3=down (visual)
  type Cell = {
    troncon: ApiTroncon;
    n_marches: number;
    x: number; y: number;
    dir: number; perp: number;
    longueur: number; largeur: number;
  };
  const cells: Cell[] = [];
  let x = 0, y = 0, dir = 0;
  const turn = (d: number, k: number) => (d + k + 4) % 4;
  const dx = [1, 0, -1, 0];
  const dy = [0, -1, 0, 1];
  niveau.troncons.forEach(t => {
    const tCalc = calc?.troncons_calc?.find((c: any) => c.troncon_id === t.id);
    cells.push({
      troncon: t, n_marches: tCalc?.n_marches ?? 0,
      x, y, dir, perp: turn(dir, 1),
      longueur: t.longueur_mm, largeur: t.largeur_mm,
    });
    x += dx[dir] * t.longueur_mm;
    y += dy[dir] * t.longueur_mm;
    if (t.type === 'quart_bas') dir = turn(dir, -1);
    else if (t.type === 'quart_haut') dir = turn(dir, 1);
  });

  // Bounding box
  let minX = 0, maxX = 0, minY = 0, maxY = 0;
  cells.forEach(c => {
    const ex = c.x + dx[c.dir] * c.longueur;
    const ey = c.y + dy[c.dir] * c.longueur;
    const px = dx[c.perp] * (c.largeur / 2);
    const py = dy[c.perp] * (c.largeur / 2);
    [c.x + px, c.x - px, ex + px, ex - px].forEach(xx => { minX = Math.min(minX, xx); maxX = Math.max(maxX, xx); });
    [c.y + py, c.y - py, ey + py, ey - py].forEach(yy => { minY = Math.min(minY, yy); maxY = Math.max(maxY, yy); });
  });
  const bboxW = Math.max(maxX - minX, 1);
  const bboxH = Math.max(maxY - minY, 1);
  const scale = Math.min((W - PAD * 2) / bboxW, (H - PAD * 2) / bboxH);
  const ox = PAD + (W - PAD * 2 - bboxW * scale) / 2 - minX * scale;
  const oy = PAD + (H - PAD * 2 - bboxH * scale) / 2 - minY * scale;
  const tx = (xx: number) => ox + xx * scale;
  const ty = (yy: number) => oy + yy * scale;

  // Ligne de foulée points (au centre de chaque cellule, à mi-largeur)
  const fouleePoints: string[] = [];
  cells.forEach(c => {
    const ex = c.x + dx[c.dir] * c.longueur;
    const ey = c.y + dy[c.dir] * c.longueur;
    fouleePoints.push(`${tx(c.x)},${ty(c.y)}`);
    fouleePoints.push(`${tx(ex)},${ty(ey)}`);
  });

  return (
    <View style={{ alignItems: 'center' }}>
      <Svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        {/* Background */}
        <Rect x={0} y={0} width={W} height={H} fill={C.BG_DEEPER} rx={12} />

        {/* Niveau cells */}
        {cells.map((c, i) => {
          const isPalier = c.troncon.type === 'palier';
          const isQuart = c.troncon.type === 'quart_bas' || c.troncon.type === 'quart_haut';
          const px = dx[c.perp] * (c.largeur / 2);
          const py = dy[c.perp] * (c.largeur / 2);
          const ex = c.x + dx[c.dir] * c.longueur;
          const ey = c.y + dy[c.dir] * c.longueur;
          const pts = [
            `${tx(c.x + px)},${ty(c.y + py)}`,
            `${tx(ex + px)},${ty(ey + py)}`,
            `${tx(ex - px)},${ty(ey - py)}`,
            `${tx(c.x - px)},${ty(c.y - py)}`,
          ].join(' ');
          const fillColor = isPalier
            ? 'rgba(91,168,199,0.12)'
            : isQuart
            ? 'rgba(245,158,11,0.10)'
            : 'rgba(140,198,63,0.08)';
          const strokeColor = isPalier ? '#5BA8C7' : isQuart ? C.WARN : C.ACCENT;

          // Steps : pour les tronçons droits = lignes parallèles ;
          //         pour les quart-tournants = lignes radiales (balancement)
          const stepEls: any[] = [];
          if (!isPalier && c.n_marches > 1) {
            if (isQuart) {
              // Marches dansantes radiales : pivot au coin intérieur du quart
              // (du côté du centre de rotation, à mi-largeur du palier balancé)
              const pivotSign = c.troncon.type === 'quart_bas' ? -1 : 1;
              const pivotX = c.x + dx[c.perp] * (c.largeur / 2) * pivotSign;
              const pivotY = c.y + dy[c.perp] * (c.largeur / 2) * pivotSign;
              for (let k = 1; k < c.n_marches; k++) {
                const step = c.longueur / c.n_marches;
                const sx = c.x + dx[c.dir] * step * k;
                const sy = c.y + dy[c.dir] * step * k;
                const ax = sx + (-dx[c.perp]) * (c.largeur) * pivotSign;
                const ay = sy + (-dy[c.perp]) * (c.largeur) * pivotSign;
                stepEls.push(
                  <Line
                    key={`step-${i}-${k}`}
                    x1={tx(pivotX)} y1={ty(pivotY)}
                    x2={tx(ax)} y2={ty(ay)}
                    stroke={strokeColor} strokeWidth={0.9} opacity={0.85}
                  />,
                );
              }
              // Pivot dot
              stepEls.push(
                <Circle key={`pivot-${i}`} cx={tx(pivotX)} cy={ty(pivotY)} r={3} fill={strokeColor} />,
              );
            } else {
              // Tronçon droit : marches parallèles
              const step = c.longueur / c.n_marches;
              for (let k = 1; k < c.n_marches; k++) {
                const sx = c.x + dx[c.dir] * step * k;
                const sy = c.y + dy[c.dir] * step * k;
                stepEls.push(
                  <Line
                    key={`step-${i}-${k}`}
                    x1={tx(sx + px)} y1={ty(sy + py)}
                    x2={tx(sx - px)} y2={ty(sy - py)}
                    stroke={strokeColor} strokeWidth={0.8} opacity={0.75}
                  />,
                );
              }
            }
          }

          // Label
          const cxr = (c.x + ex) / 2;
          const cyr = (c.y + ey) / 2;
          const label = isPalier
            ? 'PALIER'
            : c.troncon.type === 'quart_bas'
            ? `↻ ${c.n_marches}m`
            : c.troncon.type === 'quart_haut'
            ? `↺ ${c.n_marches}m`
            : `${c.n_marches} m`;

          return (
            <G key={c.troncon.id}>
              <Polygon points={pts} fill={fillColor} stroke={strokeColor} strokeWidth={1.5} />
              {stepEls}
              <SvgText
                x={tx(cxr)} y={ty(cyr) + 3}
                fontSize={9} fill={strokeColor} textAnchor="middle" fontWeight="bold"
              >
                {label}
              </SvgText>
            </G>
          );
        })}

        {/* Ligne de foulée (point milieu de chaque cellule reliés en pointillés) */}
        {cells.length > 1 && (
          <G>
            {cells.map((c, i) => {
              if (i === cells.length - 1) return null;
              const ex = c.x + dx[c.dir] * c.longueur;
              const ey = c.y + dy[c.dir] * c.longueur;
              const next = cells[i + 1];
              return (
                <Line
                  key={`foulee-${i}`}
                  x1={tx(ex)} y1={ty(ey)}
                  x2={tx(next.x)} y2={ty(next.y)}
                  stroke={C.WHITE} strokeWidth={1} strokeDasharray="2,3" opacity={0.5}
                />
              );
            })}
          </G>
        )}

        {/* Cotation largeur (sur le 1er tronçon, en bas) */}
        {cells[0] && (() => {
          const c = cells[0];
          const px = dx[c.perp] * (c.largeur / 2);
          const py = dy[c.perp] * (c.largeur / 2);
          const x1 = tx(c.x + px), y1 = ty(c.y + py);
          const x2 = tx(c.x - px), y2 = ty(c.y - py);
          return (
            <G key="cot-largeur">
              <Line x1={x1} y1={y1} x2={x2} y2={y2} stroke={C.GRAY3} strokeWidth={0.8} />
              <Polygon points={`${x1 - 4},${y1 - 3} ${x1 + 4},${y1 - 3} ${x1},${y1 + 3}`} fill={C.GRAY3} />
              <Polygon points={`${x2 - 4},${y2 - 3} ${x2 + 4},${y2 - 3} ${x2},${y2 + 3}`} fill={C.GRAY3} />
              <SvgText x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 4} fontSize={9} fill={C.WHITE} textAnchor="middle">
                L. {Math.round(c.largeur)} mm
              </SvgText>
            </G>
          );
        })()}

        {/* Start arrow */}
        {cells[0] && (
          <G>
            <Circle cx={tx(0)} cy={ty(0)} r={5} fill={C.ACCENT} />
            <SvgText x={tx(0)} y={ty(0) - 18} fontSize={9} fill={C.ACCENT} textAnchor="middle" fontWeight="bold">
              DÉPART
            </SvgText>
          </G>
        )}

        {/* Compass */}
        <G x={W - 30} y={28}>
          <Circle cx={0} cy={0} r={12} fill="transparent" stroke={C.GRAY3} strokeWidth={0.8} />
          <Line x1={0} y1={-9} x2={0} y2={9} stroke={C.GRAY3} strokeWidth={0.6} />
          <Line x1={-9} y1={0} x2={9} y2={0} stroke={C.GRAY3} strokeWidth={0.6} />
          <SvgText x={0} y={-14} fontSize={8} fill={C.GRAY3} textAnchor="middle">N</SvgText>
        </G>

        {/* Title */}
        <SvgText x={PAD} y={H - 8} fontSize={9} fill={C.GRAY3}>
          {niveau.label} · {calc?.n_steps_niveau ?? 0} marches · h {Math.round(calc?.h ?? 0)} · g {Math.round(calc?.g ?? 0)}
        </SvgText>
      </Svg>
      <Text style={styles.sketchLegend}>
        Plan de balancement à l'échelle · pointillé : ligne de foulée
      </Text>
    </View>
  );
}

// ─────────────────────────── Helpers UI ───────────────────────────

function KPICard({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <View style={styles.kpiCard}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 2 }}>
        <Text style={styles.kpiVal}>{value}</Text>
        {!!unit && <Text style={styles.kpiUnit}>{unit}</Text>}
      </View>
    </View>
  );
}

function CheckRow({
  label, icon, checked, onToggle, testID,
}: {
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  checked: boolean;
  onToggle: () => void;
  testID?: string;
}) {
  return (
    <TouchableOpacity style={styles.checkRow} onPress={onToggle} activeOpacity={0.7} testID={testID}>
      <Ionicons name={icon} size={18} color={checked ? C.ACCENT : C.GRAY3} />
      <Text style={[styles.checkLabel, !checked && { color: C.GRAY3 }]}>{label}</Text>
      <View style={[styles.checkBox, checked && styles.checkBoxOn]}>
        {checked && <Ionicons name="checkmark" size={14} color={C.DARK} />}
      </View>
    </TouchableOpacity>
  );
}

function FormatBtn({
  active, onPress, icon, label, testID,
}: {
  active: boolean;
  onPress: () => void;
  icon: any;
  label: string;
  testID?: string;
}) {
  return (
    <TouchableOpacity
      style={[styles.fmtBtn, active && styles.fmtBtnActive]}
      onPress={onPress}
      testID={testID}
    >
      <MaterialCommunityIcons name={icon} size={20} color={active ? C.DARK : C.GRAY3} />
      <Text style={[styles.fmtTxt, active && styles.fmtTxtActive]}>{label}</Text>
    </TouchableOpacity>
  );
}

// ─────────────────────────── Styles ───────────────────────────

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.DARK },
  topbar: {
    flexDirection: 'row', alignItems: 'center', padding: SP.lg,
    borderBottomWidth: 1, borderBottomColor: C.BORDER, gap: SP.md,
  },
  topbarLabel: { ...FONT.label, color: C.GRAY3, fontSize: 9 },
  topbarTitle: { ...FONT.h3, fontSize: 14, letterSpacing: 0.5 },

  section: { ...FONT.label, color: C.ACCENT, fontSize: 11, marginTop: SP.lg, marginBottom: SP.sm },

  // Sketch card
  sketchCard: {
    backgroundColor: C.CARD, borderRadius: R.lg, padding: SP.md,
    borderWidth: 1, borderColor: C.ACCENT, borderLeftWidth: 3,
  },
  sketchLegend: { ...FONT.small, fontSize: 10, marginTop: SP.sm, textAlign: 'center' },

  // KPI cards
  kpiRow: { flexDirection: 'row', gap: SP.sm },
  kpiCard: {
    flex: 1, backgroundColor: C.CARD, borderRadius: R.md,
    paddingVertical: SP.md, paddingHorizontal: SP.sm,
    alignItems: 'center',
    borderWidth: 1, borderColor: C.ACCENT, borderLeftWidth: 3, borderLeftColor: C.ACCENT,
  },
  kpiLabel: { ...FONT.label, fontSize: 9, color: C.GRAY3, marginBottom: 4 },
  kpiVal: { ...FONT.h2, color: C.ACCENT, fontSize: 20 },
  kpiUnit: { ...FONT.small, color: C.GRAY3, fontSize: 10 },

  // Blondel alert
  blondelBox: {
    flexDirection: 'row', alignItems: 'center',
    padding: SP.md, borderRadius: R.md, borderWidth: 1, borderLeftWidth: 4,
    marginTop: SP.md,
  },
  blondelBoxOk: { backgroundColor: 'rgba(140,198,63,0.08)', borderColor: C.ACCENT },
  blondelBoxWarn: { backgroundColor: 'rgba(245,158,11,0.12)', borderColor: C.WARN },
  blondelBoxError: { backgroundColor: 'rgba(239,68,68,0.10)', borderColor: C.DANGER },
  blondelTitle: { ...FONT.h3, fontSize: 14 },
  blondelHint: { ...FONT.small, fontSize: 11, marginTop: 2, lineHeight: 15 },

  // Options card
  optsCard: { backgroundColor: C.CARD, borderRadius: R.md, borderWidth: 1, borderColor: C.BORDER, overflow: 'hidden' },
  checkRow: {
    flexDirection: 'row', alignItems: 'center', gap: SP.md,
    paddingHorizontal: SP.md, paddingVertical: 14,
    borderBottomWidth: 1, borderBottomColor: C.BORDER,
  },
  checkLabel: { ...FONT.body, fontSize: 13, flex: 1 },
  checkBox: {
    width: 22, height: 22, borderRadius: 6,
    borderWidth: 1.5, borderColor: C.GRAY3,
    alignItems: 'center', justifyContent: 'center',
  },
  checkBoxOn: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },

  // Format row
  formatRow: { flexDirection: 'row', gap: SP.sm },
  fmtBtn: {
    flex: 1, alignItems: 'center', justifyContent: 'center',
    backgroundColor: C.CARD, borderRadius: R.md,
    paddingVertical: SP.md, gap: 4,
    borderWidth: 1, borderColor: C.BORDER,
  },
  fmtBtnActive: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  fmtTxt: { ...FONT.label, fontSize: 9, color: C.GRAY3, textAlign: 'center' },
  fmtTxtActive: { color: C.DARK },

  // Bottom bar
  bottomBar: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    flexDirection: 'row', gap: SP.sm, padding: SP.md,
    backgroundColor: C.DARK, borderTopWidth: 1, borderTopColor: C.BORDER,
  },
  btn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: SP.sm, paddingVertical: 14, borderRadius: R.md, borderWidth: 1,
  },
  btnGhost: { backgroundColor: C.CARD, borderColor: C.BORDER },
  btnPrimary: { backgroundColor: C.ACCENT, borderColor: C.ACCENT },
  btnTxt: { ...FONT.button, color: C.DARK, fontSize: 11 },
});
