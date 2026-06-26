import { AppShell } from './components/AppShell';
import { DemoProvider } from './hooks/useDemo';
import { TourProvider } from './hooks/useTour';

export default function App() {
  return (
    <DemoProvider>
      <TourProvider>
        <AppShell />
      </TourProvider>
    </DemoProvider>
  );
}
