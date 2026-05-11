import * as React from 'react';

// Mock for react-router-dom
export const useNavigate = () => jest.fn();
export const useLocation = () => ({ pathname: '/' });
export const useParams = () => ({});
export const useSearchParams = () => [{ get: () => '' }];
export const Navigate = () => null;
export const Outlet = () => null;
export const Route = () => null;
export const Routes = () => null;
export const Link = ({ to, children, ...props }: any) => {
  return React.createElement('a', { href: to, ...props }, children);
};
export const MemoryRouter = ({ children }: any) => React.createElement(React.Fragment, null, children);
export const BrowserRouter = ({ children }: any) => React.createElement(React.Fragment, null, children);
export const HashRouter = ({ children }: any) => React.createElement(React.Fragment, null, children);