import { render, screen } from '@testing-library/react'

import { Card, CardHeader, CardTitle, CardDescription, CardAction, CardContent, CardFooter } from './card'

describe('Card Component', () => {
  it('should render card with content', () => {
    render(<Card>Card content</Card>)
    expect(screen.getByText('Card content')).toBeInTheDocument()
  })

  it('should render with custom className', () => {
    render(<Card className="custom-class">Content</Card>)
    const card = screen.getByText('Content')
    expect(card).toHaveClass('custom-class')
  })

  it('should render card with small size', () => {
    render(<Card size="sm">Small card</Card>)
    expect(screen.getByText('Small card')).toBeInTheDocument()
  })

  it('should pass additional props to div', () => {
    render(<Card id="test-id">Content</Card>)
    const card = screen.getByText('Content')
    expect(card).toHaveAttribute('id', 'test-id')
  })
})

describe('CardHeader Component', () => {
  it('should render card header', () => {
    render(<CardHeader>Header content</CardHeader>)
    expect(screen.getByText('Header content')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(<CardHeader className="header-class">Header</CardHeader>)
    expect(screen.getByText('Header')).toHaveClass('header-class')
  })
})

describe('CardTitle Component', () => {
  it('should render card title', () => {
    render(<CardTitle>Card Title</CardTitle>)
    expect(screen.getByText('Card Title')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(<CardTitle className="title-class">Title</CardTitle>)
    expect(screen.getByText('Title')).toHaveClass('title-class')
  })
})

describe('CardDescription Component', () => {
  it('should render card description', () => {
    render(<CardDescription>Description text</CardDescription>)
    expect(screen.getByText('Description text')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(<CardDescription className="desc-class">Description</CardDescription>)
    expect(screen.getByText('Description')).toHaveClass('desc-class')
  })
})

describe('CardAction Component', () => {
  it('should render card action', () => {
    render(<CardAction>Action content</CardAction>)
    expect(screen.getByText('Action content')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(<CardAction className="action-class">Action</CardAction>)
    expect(screen.getByText('Action')).toHaveClass('action-class')
  })
})

describe('CardContent Component', () => {
  it('should render card content', () => {
    render(<CardContent>Main content</CardContent>)
    expect(screen.getByText('Main content')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(<CardContent className="content-class">Content</CardContent>)
    expect(screen.getByText('Content')).toHaveClass('content-class')
  })
})

describe('CardFooter Component', () => {
  it('should render card footer', () => {
    render(<CardFooter>Footer content</CardFooter>)
    expect(screen.getByText('Footer content')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(<CardFooter className="footer-class">Footer</CardFooter>)
    expect(screen.getByText('Footer')).toHaveClass('footer-class')
  })
})
