import {createRoot} from 'react-dom/client';
// The merged shell: every ROCK ATLAS workspace, plus the Bedrock engine's pages and real NSE data.
// The original MVP shell is kept beside it in ./App.tsx, unchanged.
import AppMerged from './AppMerged.tsx';
import './index.css';

createRoot(document.getElementById('root')!).render(<AppMerged />);
