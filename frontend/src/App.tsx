import { AppShell } from './components/AppShell';
import { DemoProvider } from './hooks/useDemo';

export default function App() {
  return (
    <DemoProvider>
      <AppShell />
    </DemoProvider>
  );
}
