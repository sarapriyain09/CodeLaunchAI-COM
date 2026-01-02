export default function Home() {
  return (
    <div className="flex flex-col items-center bg-gray-100">
      <header className="w-full bg-white shadow">
        <nav className="container mx-auto flex justify-between p-4">
          <h1 className="text-2xl font-bold">Minimalist</h1>
          <ul className="flex space-x-4">
            <li><a href="#about" className="text-gray-700 hover:text-gray-900">About</a></li>
            <li><a href="#services" className="text-gray-700 hover:text-gray-900">Services</a></li>
            <li><a href="#contact" className="text-gray-700 hover:text-gray-900">Contact</a></li>
          </ul>
        </nav>
      </header>

      <section className="w-full h-64 bg-cover bg-center" style={{ backgroundImage: 'url(https://picsum.photos/seed/hero-home/1200/700)' }}>
        <div className="flex items-center justify-center h-full bg-black bg-opacity-50">
          <h2 className="text-white text-4xl font-bold">Welcome to Minimalist</h2>
        </div>
      </section>

      <section id="about" className="container mx-auto my-8 p-4">
        <h2 className="text-3xl font-semibold mb-4">About Us</h2>
        <p className="text-gray-700 mb-4">We provide modern solutions for your everyday needs with a minimalist approach.</p>
        <img src="https://picsum.photos/seed/card-home-1/400/300" alt="Minimalist design example" className="rounded shadow-md" />
      </section>

      <section id="services" className="container mx-auto my-8 p-4">
        <h2 className="text-3xl font-semibold mb-4">Our Services</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded shadow">
            <img src="https://picsum.photos/seed/card-home-2/400/300" alt="Service 1" className="rounded mb-2" />
            <h3 className="font-bold">Service 1</h3>
            <p className="text-gray-600">Description of service 1.</p>
          </div>
          <div className="bg-white p-4 rounded shadow">
            <img src="https://picsum.photos/seed/card-home-3/400/300" alt="Service 2" className="rounded mb-2" />
            <h3 className="font-bold">Service 2</h3>
            <p className="text-gray-600">Description of service 2.</p>
          </div>
          <div className="bg-white p-4 rounded shadow">
            <img src="https://picsum.photos/seed/card-home-1/400/300" alt="Service 3" className="rounded mb-2" />
            <h3 className="font-bold">Service 3</h3>
            <p className="text-gray-600">Description of service 3.</p>
          </div>
        </div>
      </section>

      <section id="contact" className="container mx-auto my-8 p-4 text-center">
        <h2 className="text-3xl font-semibold mb-4">Get in Touch</h2>
        <p className="text-gray-700 mb-4">Have questions? Reach out to us via WhatsApp!</p>
        <a href="https://wa.me/1234567890" className="inline-block bg-green-500 text-white py-2 px-4 rounded hover:bg-green-600">
          Contact Us on WhatsApp
        </a>
      </section>

      <footer className="w-full bg-white shadow mt-8">
        <div className="container mx-auto p-4 text-center">
          <p className="text-gray-600">© 2023 Minimalist. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
