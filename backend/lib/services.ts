import path from "path";
import { promises as fs } from "fs";

export type ServiceConfig = {
  id: string;
  label: string;
};

const SERVICES_PATH = path.join(process.cwd(), "services.yaml");
const DEFAULT_SERVICES: ServiceConfig[] = [
  { id: "encampment", label: "Encampment" },
  { id: "cleaning_trash", label: "Cleaning Trash" },
  { id: "graffiti", label: "Graffiti" },
];

export async function getServices(): Promise<ServiceConfig[]> {
  try {
    const raw = await fs.readFile(SERVICES_PATH, "utf-8");
    const lines = raw.split(/\r?\n/);
    const services: ServiceConfig[] = [];
    let current: Partial<ServiceConfig> | null = null;

    const pushCurrent = () => {
      if (current?.id) {
        services.push({
          id: current.id,
          label: current.label ?? current.id,
        });
      }
      current = null;
    };

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) {
        continue;
      }
      if (trimmed.startsWith("-")) {
        pushCurrent();
        const idMatch = trimmed.match(/^-+\s*id:\s*(.+)$/);
        current = {};
        if (idMatch) {
          current.id = idMatch[1].trim();
        }
        const labelMatch = trimmed.match(/label:\s*(.+)$/);
        if (labelMatch) {
          current.label = labelMatch[1].trim();
        }
        continue;
      }
      if (!current) {
        continue;
      }
      const idMatch = trimmed.match(/^id:\s*(.+)$/);
      if (idMatch) {
        current.id = idMatch[1].trim();
      }
      const labelMatch = trimmed.match(/^label:\s*(.+)$/);
      if (labelMatch) {
        current.label = labelMatch[1].trim();
      }
    }

    pushCurrent();

    return services.length > 0 ? services : DEFAULT_SERVICES;
  } catch (error) {
    return DEFAULT_SERVICES;
  }
}
