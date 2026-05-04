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