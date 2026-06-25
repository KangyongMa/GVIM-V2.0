import {
  BoxIcon,
  ClipboardIcon,
  DatabaseIcon,
  FlaskConicalIcon,
  RotateCwIcon,
  type LucideIcon,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ScienceArtifact } from "@/core/science";
import {
  firstKetcherStructureCommand,
  ketcherCommandExpectsStructure,
  ketcherCommandMode,
  ketcherCommandsFromPayload,
  ketcherPayloadSource,
  sourceFromKetcherCommand,
  type KetcherCommand,
} from "@/core/science/ketcher-commands";
import { cn } from "@/lib/utils";

declare global {
  interface Window {
    $3Dmol?: {
      createViewer: (element: HTMLElement, options?: Record<string, unknown>) => ThreeDmolViewer;
      SurfaceType: Record<string, unknown>;
    };
  }
}

type ThreeDmolViewer = {
  clear: () => void;
  addModel: (data: string, format: string) => ThreeDmolModel;
  setStyle: (selector: Record<string, unknown>, style: Record<string, unknown>) => void;
  addSurface: (
    type: unknown,
    style: Record<string, unknown>,
    selector?: Record<string, unknown>,
  ) => void;
  addResLabels: (selector: Record<string, unknown>, style?: Record<string, unknown>) => void;
  removeAllLabels: () => void;
  setBackgroundColor: (color: string) => void;
  zoomTo: () => void;
  spin: (enabled: boolean) => void;
  resize?: () => void;
  render: () => void;
  addUnitCell?: (model: ThreeDmolModel, options?: Record<string, unknown>) => void;
  setClickable?: (
    selector: Record<string, unknown>,
    clickable: boolean,
    callback?: (atom: any, viewer: ThreeDmolViewer, event: any) => void,
  ) => void;
  addShape?: (options: Record<string, unknown>) => Record<string, unknown>;
  addLabel?: (text: string, options: Record<string, unknown>) => Record<string, unknown>;
  removeShape?: (shape: Record<string, unknown>) => void;
  removeLabel?: (label: Record<string, unknown>) => void;
  replicateUnitCell?: (a: number, b: number, c: number, model?: ThreeDmolModel) => void;
  animate?: (options: Record<string, unknown>) => void;
  stopAnimate?: () => void;
};

type ThreeDmolModel = {
  setStyle?: (style: Record<string, unknown>) => void;
};

type KetcherApi = {
  setMolecule?: (value: string) => Promise<void> | void;
  getSmiles?: () => Promise<string> | string;
  getMolfile?: () => Promise<string> | string;
  getRxn?: () => Promise<string> | string;
  getKet?: () => Promise<string> | string;
  layout?: () => Promise<void> | void;
  setSettings?: (settings: Record<string, unknown>) => Promise<void> | void;
  setZoom?: (value: number) => Promise<void> | void;
  exportImage?: (format: string) => Promise<string> | string;
  switchToMacromoleculesMode?: () => Promise<void> | void;
  switchToMoleculesMode?: () => Promise<void> | void;
};

type KetcherFrameWindow = Window & {
  ketcher?: KetcherApi;
};

type ReactionAnnotation = {
  label: string;
  value: string;
};

type KetPosition = {
  x: number;
  y: number;
  z: number;
};

const THREE_DMOL_SCRIPT_ID = "gvim-3dmol-script";
const REACTION_CONDITION_LABELS = new Set([
  "conditions",
  "condition",
  "temperature",
  "temp",
  "reagents",
  "reagent",
  "catalyst",
  "solvent",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function firstNonEmpty(...values: string[]) {
  return values.find((value) => value.length > 0) ?? "";
}

function displayValue(value: unknown): string {
  if (value === undefined || value === null) {
    return "";
  }
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return "";
  }
}

async function copyText(value: string, label: string) {
  if (!value) {
    return;
  }
  await navigator.clipboard.writeText(value);
  toast.success(`${label} copied`);
}

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function waitForKetcherApi(
  iframe: HTMLIFrameElement,
  timeoutMs = 45000,
) {
  const startedAt = performance.now();
  while (performance.now() - startedAt < timeoutMs) {
    const ketcher = (iframe.contentWindow as KetcherFrameWindow | null)
      ?.ketcher;
    if (ketcher?.setMolecule) {
      return ketcher;
    }
    await wait(100);
  }
  throw new Error("Ketcher API did not become ready");
}

async function readKetcherStructure(ketcher: KetcherApi) {
  try {
    if (ketcher.getKet) {
      const value = asString(await ketcher.getKet());
      if (value) {
        const parsed = JSON.parse(value) as Record<string, unknown>;
        const root = isRecord(parsed.root) ? parsed.root : null;
        if (root && Array.isArray(root.nodes) && root.nodes.length > 0) {
          return value;
        }
      }
      return "";
    }
    const smiles = asString(await ketcher.getSmiles?.());
    return smiles;
  } catch {
    return "";
  }
}

function hasNonEmptyMolfile(value: string) {
  if (!value) {
    return false;
  }
  if (/M\s+V30\s+BEGIN\s+ATOM/i.test(value)) {
    return true;
  }
  const countsLine = value
    .split(/\r?\n/)
    .find((line) => /\bV2000\b/i.test(line));
  const match = countsLine?.match(/^\s*(\d+)\s+(\d+)/);
  if (!match) {
    return false;
  }
  return Number(match[1]) > 0 || Number(match[2]) > 0;
}

function annotationItems(value: unknown): ReactionAnnotation[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const items: ReactionAnnotation[] = [];
  const seen = new Set<string>();
  for (const item of value) {
    if (!isRecord(item)) {
      continue;
    }
    const label = firstNonEmpty(asString(item.label), "Conditions");
    const annotationValue = asString(item.value);
    if (!annotationValue) {
      continue;
    }
    const key = `${label.toLowerCase()}:${annotationValue.toLowerCase()}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    items.push({ label, value: annotationValue });
  }
  return items;
}

function reactionAnnotationsFromPayload(
  payload: Record<string, unknown>,
): ReactionAnnotation[] {
  const command = firstKetcherStructureCommand(payload);
  const analysis = isRecord(payload.analysis) ? payload.analysis : {};
  const routeSteps = Array.isArray(analysis.route_steps)
    ? analysis.route_steps
    : [];
  return annotationItems([
    ...annotationItems(payload.annotations),
    ...annotationItems(command?.annotations),
    ...routeSteps.flatMap((step) =>
      isRecord(step) ? annotationItems(step.annotations) : [],
    ),
  ]);
}

function conditionTextFromAnnotations(annotations: ReactionAnnotation[]) {
  const preferred = annotations.filter((item) =>
    REACTION_CONDITION_LABELS.has(item.label.toLowerCase()),
  );
  const items = preferred.length > 0 ? preferred : annotations;
  const seen = new Set<string>();
  const parts: string[] = [];
  for (const item of items) {
    const label = item.label.toLowerCase();
    const normalizedValue = item.value.replace(/^[\u25b3\u0394]\s*/, "").trim();
    const key = `${label}:${normalizedValue.toLowerCase()}`;
    if (!normalizedValue || seen.has(key)) {
      continue;
    }
    seen.add(key);
    if (label === "conditions" || label === "condition") {
      parts.push(normalizedValue);
      continue;
    }
    parts.push(`${item.label}: ${normalizedValue}`);
  }
  const text = parts.join("; ");
  return text ? `\u25b3 ${text}` : "";
}

function ketPoint(value: unknown): KetPosition | null {
  if (isRecord(value)) {
    const x = Number(value.x);
    const y = Number(value.y);
    const z = Number(value.z ?? 0);
    return Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)
      ? { x, y, z }
      : null;
  }
  if (Array.isArray(value) && value.length >= 2) {
    const x = Number(value[0]);
    const y = Number(value[1]);
    const z = Number(value[2] ?? 0);
    return Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)
      ? { x, y, z }
      : null;
  }
  return null;
}

function conditionTextPosition(ket: Record<string, unknown>) {
  const root = isRecord(ket.root) ? ket.root : {};
  const nodes = Array.isArray(root.nodes) ? root.nodes : [];
  for (const node of nodes) {
    if (!isRecord(node) || asString(node.type) !== "arrow") {
      continue;
    }
    const data = isRecord(node.data) ? node.data : {};
    const points = Array.isArray(data.pos)
      ? data.pos.map(ketPoint).filter((point) => point !== null)
      : [];
    if (points.length >= 2) {
      const middle = points.reduce(
        (acc, point) => ({
          x: acc.x + point.x / points.length,
          y: acc.y + point.y / points.length,
          z: acc.z + point.z / points.length,
        }),
        { x: 0, y: 0, z: 0 },
      );
      return { x: middle.x, y: middle.y - 0.9, z: middle.z };
    }
  }
  return { x: 0, y: -1.5, z: 0 };
}

function actionNumber(value: unknown) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function positionFromAction(action: Record<string, unknown>) {
  const position = ketPoint(action.position);
  if (position) {
    return position;
  }
  const x = actionNumber(action.x);
  const y = actionNumber(action.y);
  const z = actionNumber(action.z) ?? 0;
  if (x !== null && y !== null) {
    return { x, y, z };
  }
  return null;
}

function ketcherTextContent(content: string) {
  return JSON.stringify({
    blocks: [
      {
        key: "gvim",
        text: content,
        type: "unstyled",
        depth: 0,
        inlineStyleRanges: [],
        entityRanges: [],
        data: {},
      },
    ],
    entityMap: {},
  });
}

function plainTextFromKetcherTextContent(value: string) {
  if (!value) {
    return "";
  }
  try {
    const parsed = JSON.parse(value) as unknown;
    if (!isRecord(parsed) || !Array.isArray(parsed.blocks)) {
      return value;
    }
    return parsed.blocks
      .map((block) => (isRecord(block) ? asString(block.text) : ""))
      .filter(Boolean)
      .join("\n")
      .trim();
  } catch {
    return value.trim();
  }
}

function textBoxForPosition(position: KetPosition, content: string) {
  const width = Math.max(1.2, content.length * 0.24);
  const height = 0.45;
  return [
    position,
    { x: position.x, y: position.y - height, z: position.z },
    { x: position.x + width, y: position.y - height, z: position.z },
    { x: position.x + width, y: position.y, z: position.z },
  ];
}

function textContentFromKetNode(node: unknown) {
  if (!isRecord(node)) {
    return "";
  }
  const data = isRecord(node.data) ? node.data : {};
  const content = firstNonEmpty(
    asString(data.content),
    asString(node.content),
    asString(node.text),
  );
  return plainTextFromKetcherTextContent(content);
}

async function injectReactionAnnotations(
  ketcher: KetcherApi,
  annotations: ReactionAnnotation[],
) {
  const conditionText = conditionTextFromAnnotations(annotations);
  if (!conditionText || !ketcher.getKet || !ketcher.setMolecule) {
    return;
  }
  await addKetcherText(ketcher, conditionText);
}

async function addKetcherText(
  ketcher: KetcherApi,
  content: string,
  position?: KetPosition | null,
) {
  if (!content || !ketcher.getKet || !ketcher.setMolecule) {
    return;
  }
  const ket = JSON.parse(String(await ketcher.getKet())) as Record<string, unknown>;
  const root = isRecord(ket.root) ? ket.root : null;
  const nodes = root?.nodes;
  if (!root || !Array.isArray(nodes)) {
    return;
  }
  const nextNodes = nodes.filter(
    (node) => textContentFromKetNode(node) !== content,
  );
  const textPosition = position ?? conditionTextPosition(ket);
  nextNodes.push({
    type: "text",
    data: {
      content: ketcherTextContent(content),
      position: textPosition,
      pos: textBoxForPosition(textPosition, content),
    },
  });
  root.nodes = nextNodes;
  await ketcher.setMolecule(JSON.stringify(ket));
}

async function injectKetcherPayload({
  iframe,
  source,
  payload,
  annotations,
}: {
  iframe: HTMLIFrameElement | null;
  source: string;
  payload: Record<string, unknown>;
  annotations: ReactionAnnotation[];
}) {
  const commands = ketcherCommandsFromPayload(payload);
  if (!iframe || (!source && commands.length === 0)) {
    return;
  }
  const ketcher = await waitForKetcherApi(iframe);
  const didApplyCommands = await applyKetcherCommands(ketcher, commands);
  if (!didApplyCommands && source && ketcher.setMolecule) {
    await ketcher.setMolecule(source);
  }
  await injectReactionAnnotations(ketcher, annotations);

  const expectsStructure = Boolean(
    source ||
      commands.some((command) => ketcherCommandExpectsStructure(command)),
  );
  if (!expectsStructure) {
    return;
  }

  for (let attempt = 0; attempt < 20; attempt += 1) {
    if (await readKetcherStructure(ketcher)) {
      return;
    }
    await wait(100);
  }
  throw new Error("Ketcher accepted the payload but the canvas stayed empty");
}

async function applyKetcherCommand(
  ketcher: KetcherApi,
  command: KetcherCommand,
) {
  if (command.type === "open_editor") {
    return false;
  }
  if (
    command.type === "load_molecule" ||
    command.type === "load_reaction" ||
    command.type === "load_ket"
  ) {
    const source = sourceFromKetcherCommand(command);
    if (!source || !ketcher.setMolecule) {
      return false;
    }
    await ketcher.setMolecule(source);
    return true;
  }
  if (command.type === "add_text") {
    const content = firstNonEmpty(
      asString(command.content),
      asString(command.text),
      asString(command.value),
    );
    await addKetcherText(ketcher, content, positionFromAction(command));
    return false;
  }
  if (command.type === "layout") {
    await ketcher.layout?.();
    return false;
  }
  if (command.type === "set_zoom") {
    const zoom = actionNumber(command.zoom ?? command.value);
    if (zoom !== null) {
      await ketcher.setZoom?.(zoom);
    }
    return false;
  }
  if (command.type === "set_settings") {
    const settings = isRecord(command.settings) ? command.settings : {};
    await ketcher.setSettings?.(settings);
    return false;
  }
  if (command.type === "switch_mode") {
    const mode = ketcherCommandMode(command);
    if (mode === "molecules") {
      await ketcher.switchToMoleculesMode?.();
    }
    if (mode === "macromolecules") {
      await ketcher.switchToMacromoleculesMode?.();
    }
    return false;
  }
  if (command.type === "clear") {
    await ketcher.setMolecule?.("");
    return false;
  }
  return false;
}

async function applyKetcherCommands(
  ketcher: KetcherApi,
  commands: KetcherCommand[],
) {
  let appliedStructure = false;
  for (const command of commands) {
    const commandAppliedStructure = await applyKetcherCommand(ketcher, command);
    appliedStructure = appliedStructure || commandAppliedStructure;
  }
  return appliedStructure;
}

function metricEntries(payload: Record<string, unknown>): Array<[string, string]> {
  const descriptors = isRecord(payload.descriptors) ? payload.descriptors : {};
  const keys = [
    "formula",
    "normalized_formula",
    "reduced_formula",
    "chemical_system",
    "material_id",
    "source",
    "engine",
    "molar_mass_g_mol",
    "density",
    "space_group",
    "energy_above_hull",
    "band_gap",
  ];

  return keys
    .map((key) => {
      const value = payload[key] ?? descriptors[key];
      if (value === undefined || value === null || value === "") {
        return null;
      }
      return [key, displayValue(value)];
    })
    .filter((entry): entry is [string, string] => entry !== null);
}

function ArtifactHeader({
  artifact,
  icon: Icon,
}: {
  artifact: ScienceArtifact;
  icon: LucideIcon;
}) {
  return (
    <div className="flex min-w-0 items-center justify-between gap-3 border-b px-4 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <div className="bg-muted flex size-9 shrink-0 items-center justify-center rounded-md">
          <Icon className="size-4" />
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{artifact.title}</div>
          <div className="text-muted-foreground truncate text-xs">
            {artifact.toolKey ?? artifact.toolName ?? artifact.kind}
          </div>
        </div>
      </div>
      <Badge className="rounded" variant="secondary">
        {artifact.kind}
      </Badge>
    </div>
  );
}

function KetcherArtifact({ artifact }: { artifact: ScienceArtifact }) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const lastInjectedRef = useRef<string>("");
  const [loadVersion, setLoadVersion] = useState(0);
  const { smiles, molfile, source } = useMemo(
    () => ketcherPayloadSource(artifact.payload),
    [artifact.payload],
  );
  const commands = useMemo(
    () => ketcherCommandsFromPayload(artifact.payload),
    [artifact.payload],
  );
  const annotations = useMemo(
    () => reactionAnnotationsFromPayload(artifact.payload),
    [artifact.payload],
  );

  const payloadKey = useMemo(() => {
    return JSON.stringify({ source, commands, annotations });
  }, [source, commands, annotations]);

  const applyPayload = useCallback(
    async (notify = false) => {
      try {
        lastInjectedRef.current = payloadKey;
        await injectKetcherPayload({
          iframe: iframeRef.current,
          source,
          payload: artifact.payload,
          annotations,
        });
        if (notify) {
          toast.success("Ketcher structure loaded");
        }
      } catch (error) {
        console.error(error);
        if (notify) {
          toast.error("Ketcher structure failed to load");
        }
      }
    },
    [annotations, artifact.payload, source, payloadKey],
  );

  useEffect(() => {
    if (loadVersion > 0 && (source || commands.length > 0)) {
      if (lastInjectedRef.current === payloadKey) {
        return;
      }
      void applyPayload(false);
    }
  }, [commands.length, applyPayload, loadVersion, source, payloadKey]);

  return (
    <section className="overflow-hidden rounded-lg border">
      <ArtifactHeader artifact={artifact} icon={FlaskConicalIcon} />
      <div className="flex flex-wrap gap-2 border-b px-4 py-2">
        {smiles && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => void copyText(smiles, "SMILES")}
          >
            <ClipboardIcon className="size-4" />
            SMILES
          </Button>
        )}
        {molfile && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => void copyText(molfile, "Molfile")}
          >
            <ClipboardIcon className="size-4" />
            Molfile
          </Button>
        )}
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => void applyPayload(true)}
        >
          <RotateCwIcon className="size-4" />
          Reload
        </Button>
      </div>
      <iframe
        ref={iframeRef}
        className="h-[520px] w-full bg-white"
        src="/vendor/ketcher-3.12.0/index.html"
        onLoad={() => setLoadVersion((version) => version + 1)}
      />
    </section>
  );
}

function loadThreeDmolScript() {
  if (window.$3Dmol) {
    return Promise.resolve();
  }
  const existing = document.getElementById(THREE_DMOL_SCRIPT_ID);
  if (existing) {
    return new Promise<void>((resolve) => {
      const timer = window.setInterval(() => {
        if (window.$3Dmol) {
          window.clearInterval(timer);
          resolve();
        }
      }, 50);
    });
  }
  return new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.id = THREE_DMOL_SCRIPT_ID;
    script.src = "/vendor/3dmol/3Dmol-min.js";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load 3Dmol"));
    document.head.appendChild(script);
  });
}

function ThreeDArtifact({ artifact }: { artifact: ScienceArtifact }) {
  const viewerRef = useRef<HTMLDivElement | null>(null);
  const viewerInstanceRef = useRef<ThreeDmolViewer | null>(null);
  const [style, setStyle] = useState("stick");
  const [surface, setSurface] = useState(false);
  const [spin, setSpin] = useState(false);
  const [labels, setLabels] = useState(false);
  const [animateState, setAnimateState] = useState(false);
  const [measureMode, setMeasureMode] = useState(false);
  const [hasMeasures, setHasMeasures] = useState(false);
  const [redrawCounter, setRedrawCounter] = useState(0);

  const measurementsRef = useRef<
    Array<{
      start: { x: number; y: number; z: number };
      end: { x: number; y: number; z: number };
      distance: number;
    }>
  >([]);
  const firstAtomRef = useRef<any>(null);

  const pdbBlock = asString(artifact.payload.pdb_block);
  const molblock = asString(artifact.payload.molblock);
  const format = pdbBlock ? "pdb" : "mol";
  const structure = pdbBlock || molblock;

  const clearMeasures = useCallback(() => {
    measurementsRef.current = [];
    firstAtomRef.current = null;
    setHasMeasures(false);
    setRedrawCounter((prev) => prev + 1);
    toast.success("Measurements cleared");
  }, []);

  useEffect(() => {
    const element = viewerRef.current;
    if (!element) {
      return;
    }
    const observer = new ResizeObserver(() => {
      const viewer = viewerInstanceRef.current;
      viewer?.resize?.();
      viewer?.render();
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);



  useEffect(() => {
    let cancelled = false;
    void loadThreeDmolScript()
      .then(() => {
        if (cancelled || !viewerRef.current || !window.$3Dmol || !structure) {
          return;
        }
        const viewer =
          viewerInstanceRef.current ??
          window.$3Dmol.createViewer(viewerRef.current, {
            backgroundColor: "white",
          });
        viewerInstanceRef.current = viewer;
        viewer.clear();
        const model = viewer.addModel(structure, format);
        model.setStyle?.({});
        if (style === "line") {
          viewer.setStyle({}, { line: {} });
        } else if (style === "sphere") {
          viewer.setStyle({}, { sphere: { scale: 0.3 } });
        } else if (style === "cartoon") {
          viewer.setStyle({}, { cartoon: { color: "spectrum" } });
        } else if (style === "ribbon") {
          viewer.setStyle({}, { ribbon: { color: "spectrum" } });
        } else {
          viewer.setStyle({}, { stick: { radius: 0.16 }, sphere: { scale: 0.22 } });
        }

        if (surface) {
          // If labels or measureMode is enabled, auto render VDW surface as a beautiful,
          // high-transparency wireframe mesh to fully prevent visual blockage inside the molecule!
          const useWireframe = measureMode || labels;
          viewer.addSurface(window.$3Dmol.SurfaceType.VDW, {
            opacity: useWireframe ? 0.16 : 0.25,
            color: "white",
            wireframe: useWireframe,
          });
        }

        if (labels) {
          viewer.addResLabels({}, { fontSize: 11, showBackground: false });
        } else {
          viewer.removeAllLabels();
        }

        // Redraw all saved atom-to-atom distance measurements
        measurementsRef.current.forEach((m) => {
          viewer.addShape?.({
            type: "cylinder",
            start: m.start,
            end: m.end,
            radius: 0.05,
            color: "grey",
            dashed: true,
          });
          viewer.addLabel?.(`${m.distance.toFixed(3)} Å`, {
            position: {
              x: (m.start.x + m.end.x) / 2,
              y: (m.start.y + m.end.y) / 2,
              z: (m.start.z + m.end.z) / 2,
            },
            backgroundColor: "white",
            backgroundOpacity: 0.8,
            fontColor: "black",
            fontSize: 12,
          });
        });

        // Set up interactive click-to-measure events if enabled
        if (measureMode) {
          viewer.setClickable?.({}, true, (atom: any) => {
            if (!firstAtomRef.current) {
              firstAtomRef.current = atom;
              toast.info(
                `Selected ${atom.elem}${atom.serial ?? ""}. Click a second atom.`,
              );
            } else {
              const atom1 = firstAtomRef.current;
              const atom2 = atom;
              if (atom1.serial === atom2.serial && atom1.serial !== undefined) {
                firstAtomRef.current = null;
                toast.warning("Selected the same atom. Click another.");
                return;
              }
              const dx = atom1.x - atom2.x;
              const dy = atom1.y - atom2.y;
              const dz = atom1.z - atom2.z;
              const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

              measurementsRef.current.push({
                start: { x: atom1.x, y: atom1.y, z: atom1.z },
                end: { x: atom2.x, y: atom2.y, z: atom2.z },
                distance: dist,
              });
              firstAtomRef.current = null;
              setHasMeasures(true);
              setRedrawCounter((prev) => prev + 1);
              toast.success(`Distance: ${dist.toFixed(3)} Å`);
            }
          });
        } else {
          viewer.setClickable?.({}, false);
          firstAtomRef.current = null;
        }

        // Native 3Dmol.js Multi-frame Animation
        if (animateState) {
          viewer.animate?.({ loop: "forward", step: 1 });
        } else {
          viewer.stopAnimate?.();
        }

        viewer.setBackgroundColor("white");
        viewer.resize?.();
        viewer.zoomTo();
        viewer.spin(spin);
        viewer.render();
      })
      .catch((error) => {
        console.error(error);
      });
    return () => {
      cancelled = true;
    };
  }, [
    format,
    labels,
    spin,
    structure,
    style,
    surface,
    measureMode,
    animateState,
    redrawCounter,
  ]);

  return (
    <section className="relative isolate overflow-hidden rounded-lg border">
      <ArtifactHeader artifact={artifact} icon={BoxIcon} />
      <div className="flex flex-wrap items-center gap-2 border-b px-4 py-2">
        <select
          className="border-input bg-background h-8 rounded-md border px-2 text-sm"
          value={style}
          onChange={(event) => setStyle(event.target.value)}
        >
          <option value="stick">Stick</option>
          <option value="line">Line</option>
          <option value="sphere">Sphere</option>
          <option value="cartoon">Cartoon</option>
          <option value="ribbon">Ribbon</option>
        </select>
        <Button
          type="button"
          size="sm"
          variant={surface ? "default" : "outline"}
          onClick={() => setSurface((value) => !value)}
        >
          Surface
        </Button>
        <Button
          type="button"
          size="sm"
          variant={labels ? "default" : "outline"}
          onClick={() => setLabels((value) => !value)}
        >
          Labels
        </Button>

        <Button
          type="button"
          size="sm"
          variant={measureMode ? "default" : "outline"}
          onClick={() => {
            setMeasureMode((value) => !value);
            firstAtomRef.current = null;
          }}
        >
          Measure
        </Button>
        {hasMeasures && (
          <Button
            type="button"
            size="sm"
            variant="destructive"
            onClick={clearMeasures}
          >
            Clear Measures
          </Button>
        )}
        <Button
          type="button"
          size="sm"
          variant={animateState ? "default" : "outline"}
          onClick={() => setAnimateState((value) => !value)}
        >
          Animate
        </Button>
        <Button
          type="button"
          size="sm"
          variant={spin ? "default" : "outline"}
          onClick={() => setSpin((value) => !value)}
        >
          Spin
        </Button>
      </div>
      <div
        ref={viewerRef}
        className="relative z-0 h-[460px] w-full overflow-hidden bg-white [&>canvas]:!absolute [&>canvas]:!inset-0 [&>canvas]:!h-full [&>canvas]:!w-full"
      />
    </section>
  );
}

function MaterialsArtifact({ artifact }: { artifact: ScienceArtifact }) {
  const metrics = useMemo(() => metricEntries(artifact.payload), [artifact.payload]);
  const results = Array.isArray(artifact.payload.results)
    ? artifact.payload.results.filter(isRecord)
    : [];
  return (
    <section className="overflow-hidden rounded-lg border">
      <ArtifactHeader artifact={artifact} icon={DatabaseIcon} />
      <div className="space-y-4 p-4">
        {metrics.length > 0 && (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {metrics.map(([key, value]) => (
              <div key={key} className="bg-muted/40 rounded-md p-3">
                <div className="text-muted-foreground text-[11px] uppercase">
                  {key.replaceAll("_", " ")}
                </div>
                <div className="mt-1 break-words text-sm font-medium">{value}</div>
              </div>
            ))}
          </div>
        )}
        {results.length > 0 && (
          <div className="overflow-x-auto rounded-md border">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="bg-muted/60 text-muted-foreground">
                <tr>
                  {["material_id", "formula_pretty", "band_gap", "energy_above_hull", "formation_energy_per_atom"].map(
                    (key) => (
                      <th key={key} className="px-3 py-2 text-left font-medium">
                        {key.replaceAll("_", " ")}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {results.map((row, index) => (
                  <tr
                    key={displayValue(row.material_id) || String(index)}
                    className="border-t"
                  >
                    {[
                      "material_id",
                      "formula_pretty",
                      "band_gap",
                      "energy_above_hull",
                      "formation_energy_per_atom",
                    ].map((key) => (
                      <td key={key} className="px-3 py-2">
                        {displayValue(row[key])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <details className="rounded-md border">
          <summary className="cursor-pointer px-3 py-2 text-sm font-medium">
            Structured payload
          </summary>
          <pre className="max-h-80 overflow-auto border-t p-3 text-xs whitespace-pre-wrap">
            {JSON.stringify(artifact.payload, null, 2)}
          </pre>
        </details>
      </div>
    </section>
  );
}

function ScienceArtifactItem({ artifact }: { artifact: ScienceArtifact }) {
  if (artifact.kind === "ketcher") {
    return <KetcherArtifact artifact={artifact} />;
  }
  if (artifact.kind === "three-d") {
    return <ThreeDArtifact artifact={artifact} />;
  }
  return <MaterialsArtifact artifact={artifact} />;
}

export function ScienceArtifactStack({
  artifacts,
  className,
}: {
  artifacts: ScienceArtifact[];
  className?: string;
}) {
  if (artifacts.length === 0) {
    return null;
  }
  return (
    <div className={cn("mt-3 flex w-full flex-col gap-3", className)}>
      {artifacts.map((artifact) => (
        <ScienceArtifactItem key={artifact.id} artifact={artifact} />
      ))}
    </div>
  );
}
