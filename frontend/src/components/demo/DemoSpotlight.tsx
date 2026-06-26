import { useDemo } from '../../hooks/useDemo';
import { SpotlightOverlay } from '../tour/SpotlightOverlay';

/**
 * During the guided demo, gently spotlights the functional UI region the current
 * beat is using (graph, chat, intake, insights, metrics). Highlight-only and
 * non-blocking — the demo caption supplies the words; this points at the region.
 */
export function DemoSpotlight() {
  const { active, spotlightAnchor } = useDemo();
  if (!active || !spotlightAnchor) return null;
  return <SpotlightOverlay anchor={spotlightAnchor} autoMode />;
}
