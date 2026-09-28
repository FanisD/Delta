import layoutsJson from "../../shared/layouts.json"
import type { Layout } from "./api"

export type LayoutSpec = {
  id: Layout
  label: string
  description: string
  regions: string[]
  slots: string[]
}

export const layoutSpecs = layoutsJson as LayoutSpec[]
